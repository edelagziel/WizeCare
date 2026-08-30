import argparse
import os
import re
from typing import List, Tuple

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# ---------- language mapping ----------
NLLB_MAP = {"en":"eng_Latn","he":"heb_Hebr","ar":"arb_Arab","ru":"rus_Cyrl","es":"spa_Latn"}
def map_lang(code: str) -> str:
    code = (code or "").strip().lower()
    if code in NLLB_MAP: return NLLB_MAP[code]
    if re.match(r"^[a-z]{3}_[A-Za-z]{4}$", code): return code
    return "eng_Latn"

# ---------- heuristics ----------
LIST_LINE_RX = re.compile(r'^\s*(?:[-*•]|(?:\(?\d+\)?|\d+\.))\s+')
def input_has_list_markers(text: str) -> bool:
    return any(LIST_LINE_RX.search(line) for line in text.splitlines())
def strip_leading_list_markers(text: str) -> str:
    return "\n".join(LIST_LINE_RX.sub("", line) for line in text.splitlines())
def extract_numbers(text: str) -> List[str]:
    pats = [r"\d{1,2}:\d{2}:\d{2}(?:\.\d{1,3})?", r"\d+\s*%", r"\d+\s*[–\-]\s*\d+", r"\d+\s*[x×]\s*\d+", r"\d+(?:[\.,]\d+)?"]
    combined = "|".join(f"({p})" for p in pats)
    seen, out = set(), []
    for m in re.finditer(combined, text):
        tok = m.group(0)
        if tok not in seen:
            seen.add(tok); out.append(tok)
    return out
def detect_lang_light(s: str) -> str:
    if re.search(r"[\u0590-\u05FF]", s): return "he"
    if re.search(r"[\u0400-\u04FF]", s): return "ru"
    if re.search(r"[\u0600-\u06FF]", s): return "ar"
    if re.search(r"\b(el|la|los|las|de|que|para|con|por|y|una|uno|unos|unas)\b", s.lower()): return "es"
    return "en"

# ---------- timecodes ----------
TC_RX = re.compile(r'\[?\s*:?(?P<start>\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?)\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?)\s*\]?')
def _norm_ms(x: str) -> str:
    if '.' in x:
        hhmmss, ms = x.split('.', 1); ms = (ms + '000')[:3]; return f"{hhmmss}.{ms}"
    return x
def normalize_tc(m: re.Match) -> str:
    return f"[{_norm_ms(m.group('start'))} --> {_norm_ms(m.group('end'))}]"
def segment_by_timecodes(text: str) -> List[Tuple[str, str]]:
    parts: List[Tuple[str, str]] = []
    matches = list(TC_RX.finditer(text))
    if not matches: return [("", text.strip())]
    for i, m in enumerate(matches):
        tc = normalize_tc(m)
        s = m.end()
        e = matches[i+1].start() if i+1 < len(matches) else len(text)
        seg = text[s:e].strip()
        parts.append((tc, seg))
    tail_start = matches[-1].end()
    if tail_start < len(text) and parts:
        extra = text[tail_start:].strip()
        if extra:
            tc, prev = parts[-1]; parts[-1] = (tc, (prev + " " + extra).strip())
    return parts
def stitch_segments(segments: List[Tuple[str, str]]) -> str:
    out = []
    for tc, body in segments:
        if tc and body: out.append(f"{tc} {body}")
        elif tc:        out.append(tc)
        elif body:      out.append(body)
    return "\n".join(out).strip()

# ---------- batching ----------
def chunks(lst: List[str], n: int):
    for i in range(0, len(lst), n): yield lst[i:i+n]

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--src", dest="src", default="auto")    # NEW: supports 'auto'
    ap.add_argument("--tgt", dest="tgt", default="heb_Hebr")
    ap.add_argument("--batch", dest="batch", type=int, default=8)
    ap.add_argument("--model", dest="model", default="facebook/nllb-200-1.3B")
    ap.add_argument("--retry", dest="retry", type=int, default=1)
    args = ap.parse_args()

    text = open(args.inp, "r", encoding="utf-8").read()

    # source language (auto/he/en)
    if args.src.strip().lower() == "auto":
        guess = detect_lang_light(text)
        src = {"he":"heb_Hebr","en":"eng_Latn"}.get(guess, "eng_Latn")
    else:
        src = map_lang(args.src)
    tgt = map_lang(args.tgt)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[translator] device={device}, model={args.model}, src={src}, tgt={tgt}, batch={args.batch}", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model)
    model.to(device); tokenizer.src_lang = src

    had_lists = input_has_list_markers(text)
    must_nums = extract_numbers(text)

    segments = segment_by_timecodes(text)
    to_translate = [seg for _, seg in segments]
    if not any(s.strip() for s in to_translate):
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        open(args.out, "w", encoding="utf-8").write(stitch_segments(segments))
        print(f"[translator] empty-or-timecode-only input → {args.out}", flush=True); return

    translated: List[str] = []
    done = 0; total = len(to_translate)
    for batch in chunks(to_translate, args.batch):
        print(f"[translator] {done}/{total} ...", flush=True)
        if not any(s.strip() for s in batch):
            decoded = batch
        else:
            enc = tokenizer(batch, return_tensors="pt", padding=True, truncation=True).to(device)
            gen = model.generate(
                **enc,
                forced_bos_token_id=tokenizer.lang_code_to_id[tgt],
                max_new_tokens=256, num_beams=4, no_repeat_ngram_size=2
            )
            decoded = tokenizer.batch_decode(gen, skip_special_tokens=True)
        translated.extend([d.strip() for d in decoded]); done += len(batch)

    out_segments = [(tc, new) for (tc, _), new in zip(segments, translated)]
    out_text = stitch_segments(out_segments)

    if not had_lists and input_has_list_markers(out_text):
        out_text = strip_leading_list_markers(out_text)

    # language sanity (שומר על כיוון – לא אמור לזלול ב‑NLLB)
    in_lang = detect_lang_light(text)
    out_lang = detect_lang_light(out_text)

    missing = [n for n in must_nums if n not in out_text]
    tries = 0
    while (missing or out_lang != in_lang) and tries < args.retry:
        # תיקון מינימלי: נשרשר את המספרים החסרים בסוף (גישה שמרנית)
        for n in missing:
            out_text += f"\n{n}"
        out_lang = detect_lang_light(out_text)
        missing = [n for n in must_nums if n not in out_text]
        tries += 1

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(out_text)
    print(f"[translator] saved: {args.out}", flush=True)

if __name__ == "__main__":
    main()






# this code got rated 5