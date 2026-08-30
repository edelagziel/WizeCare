#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import re
from typing import List, Tuple

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# ============ Language mapping ============
NLLB_MAP = {
    "en": "eng_Latn",
    "he": "heb_Hebr",
    "ar": "arb_Arab",
    "ru": "rus_Cyrl",
    "es": "spa_Latn",
}

def map_lang(code: str) -> str:
    code = (code or "").strip().lower()
    if code in NLLB_MAP:
        return NLLB_MAP[code]
    # already NLLB code?
    if re.match(r"^[a-z]{3}_[A-Za-z]{4}$", code):
        return code
    return "eng_Latn"

# ============ Light heuristics ============
LIST_LINE_RX = re.compile(r'^\s*(?:[-*•]|(?:\(?\d+\)?|\d+\.))\s+')
def input_has_list_markers(text: str) -> bool:
    return any(LIST_LINE_RX.search(line) for line in text.splitlines())

def strip_leading_list_markers(text: str) -> str:
    return "\n".join(LIST_LINE_RX.sub("", line) for line in text.splitlines())

def extract_numbers(text: str) -> List[str]:
    pats = [
        r"\d{1,2}:\d{2}:\d{2}(?:\.\d{1,3})?",  # timestamps
        r"\d+\s*%",                            # percents
        r"\d+\s*[–\-]\s*\d+",                  # ranges 1–2 / 1-2
        r"\d+\s*[x×]\s*\d+",                   # sets/reps 3x10 / 3×10
        r"\d+(?:[\.,]\d+)?",                   # numbers
    ]
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

# ============ Timecodes ============
# Flexible: optional [ ], optional leading ':', optional milliseconds
TC_RX = re.compile(
    r'\[?\s*:?(?P<start>\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?)\s*-->\s*'
    r'(?P<end>\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?)\s*\]?'
)

def _norm_ms(x: str) -> str:
    if '.' in x:
        hhmmss, ms = x.split('.', 1)
        ms = (ms + '000')[:3]
        return f"{hhmmss}.{ms}"
    return x

def normalize_tc(m: re.Match) -> str:
    return f"[{_norm_ms(m.group('start'))} --> {_norm_ms(m.group('end'))}]"

def segment_by_timecodes(text: str) -> List[Tuple[str, str]]:
    """
    Returns [(tc, segment_text), ...] – each timecode is paired with the text
    that follows it until the next timecode or EOF. If no TCs: [("", full_text)].
    """
    parts: List[Tuple[str, str]] = []
    matches = list(TC_RX.finditer(text))
    if not matches:
        return [("", text.strip())]

    for i, m in enumerate(matches):
        tc = normalize_tc(m)
        s = m.end()
        e = matches[i+1].start() if i+1 < len(matches) else len(text)
        seg = text[s:e].strip()
        parts.append((tc, seg))

    # tail text after last TC (append to last)
    tail_start = matches[-1].end()
    if tail_start < len(text) and parts:
        extra = text[tail_start:].strip()
        if extra:
            tc, prev = parts[-1]
            parts[-1] = (tc, (prev + " " + extra).strip())
    return parts

def stitch_segments(segments: List[Tuple[str, str]]) -> str:
    """Join back as '[TC] <translated>' per line."""
    out = []
    for tc, body in segments:
        if tc and body: out.append(f"{tc} {body}")
        elif tc:        out.append(tc)
        elif body:      out.append(body)
    return "\n".join(out).strip()

# ============ Batching ============
def chunks(lst: List[str], n: int):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]

# ============ Translate ============

def translate_segments(segments: List[Tuple[str, str]],
                       tokenizer, model, tgt_code: str,
                       device: str, batch_size: int) -> List[str]:
    """
    Translates only the segment texts (without TCs). Default is conservative batching
    (keeps quality close to sentence-by-sentence).
    """
    texts = [seg for _, seg in segments]
    out: List[str] = []
    done, total = 0, len(texts)
    if total == 0:
        return out

    # Conservative default to keep quality; let user raise via --batch
    bs = max(1, batch_size)

    for batch in chunks(texts, bs):
        # If everything in batch is empty → keep empty
        if not any(s.strip() for s in batch):
            out.extend(batch)
            done += len(batch)
            print(f"[translator] {done}/{total} ...", flush=True)
            continue

        enc = tokenizer(batch, return_tensors="pt", padding=True, truncation=True).to(device)
        gen = model.generate(
            **enc,
            forced_bos_token_id=tokenizer.lang_code_to_id[tgt_code],
            max_new_tokens=256,
            num_beams=4,
            no_repeat_ngram_size=2,
        )
        decoded = tokenizer.batch_decode(gen, skip_special_tokens=True)
        out.extend([d.strip() for d in decoded])
        done += len(batch)
        print(f"[translator] {done}/{total} ...", flush=True)

    return out

# ============ Main ============

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in",  dest="inp",  required=True, help="path to input .txt")
    ap.add_argument("--out", dest="out",  required=True, help="path to output .txt")
    ap.add_argument("--src", dest="src",  default="auto", help="source language: he/en/auto or NLLB code")
    ap.add_argument("--tgt", dest="tgt",  default="heb_Hebr", help="target language: he/en/ar/ru/es or NLLB code")
    ap.add_argument("--batch", dest="batch", type=int, default=1, help="segments per batch (default 1 for quality)")
    ap.add_argument("--model", dest="model", default="facebook/nllb-200-1.3B", help="HF model id")
    ap.add_argument("--retry", dest="retry", type=int, default=0, help="minimal retry if numerals missing")
    args = ap.parse_args()

    raw = open(args.inp, "r", encoding="utf-8").read()

    # source language (auto/he/en/explicit code)
    if args.src.strip().lower() == "auto":
        guess = detect_lang_light(raw)
        src_code = {"he":"heb_Hebr", "en":"eng_Latn"}.get(guess, "eng_Latn")
    else:
        src_code = map_lang(args.src)

    tgt_code = map_lang(args.tgt)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[translator] device={device}, model={args.model}, src={src_code}, tgt={tgt_code}, batch={args.batch}", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model)
    model.to(device)
    tokenizer.src_lang = src_code

    # Guardrails
    had_lists  = input_has_list_markers(raw)
    must_nums  = extract_numbers(raw)

    # Segment by timecodes (or single segment if none)
    segments = segment_by_timecodes(raw)   # [(tc, seg_text), ...]
    if not any(seg.strip() for _, seg in segments):
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        open(args.out, "w", encoding="utf-8").write(stitch_segments(segments))
        print(f"[translator] empty-or-timecode-only input → {args.out}", flush=True)
        return

    # Translate segment texts
    translated_texts = translate_segments(segments, tokenizer, model, tgt_code, device, args.batch)

    # Re-attach timecodes
    out_segments = [(tc, new) for (tc, _), new in zip(segments, translated_texts)]
    out_text = stitch_segments(out_segments)

    # If input had no list markers but model added some, strip them
    if not had_lists and input_has_list_markers(out_text):
        out_text = strip_leading_list_markers(out_text)

    # Minimal numerals check (do not invent numbers!)
    missing = [n for n in must_nums if n not in out_text]
    tries = 0
    while missing and tries < max(0, args.retry):
        # אסטרטגיה שמרנית: אם חסר מספר, נוסיף אותו כטקסט גלוי בסוף המקטע האחרון שבו הופיע המקור.
        # לא נעשה “תיקון חכם” אוטומטי כדי לא להמציא הקשרים.
        out_text += "\n" + " ".join(missing)
        tries += 1
        missing = [n for n in must_nums if n not in out_text]

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(out_text)

    print(f"[translator] saved: {args.out}", flush=True)

if __name__ == "__main__":
    main()
