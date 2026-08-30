#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import re
from typing import List, Tuple

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# ---------- language mapping ----------
NLLB_MAP = {"en": "eng_Latn", "he": "heb_Hebr", "ar": "arb_Arab", "ru": "rus_Cyrl", "es": "spa_Latn"}

def map_lang(code: str) -> str:
    code = (code or "").strip().lower()
    if code in NLLB_MAP:
        return NLLB_MAP[code]
    if re.match(r"^[a-z]{3}_[A-Za-z]{4}$", code):
        return code
    return "eng_Latn"

# ---------- lightweight lang detection ----------
def detect_lang_light(s: str) -> str:
    if re.search(r"[\u0590-\u05FF]", s): return "he"
    if re.search(r"[\u0400-\u04FF]", s): return "ru"
    if re.search(r"[\u0600-\u06FF]", s): return "ar"
    if re.search(r"\b(el|la|los|las|de|que|para|con|por|y|una|uno|unos|unas)\b", s.lower()): return "es"
    return "en"

# ---------- timecodes ----------
TC_RX = re.compile(
    r'\[?\s*:?(?P<start>\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?)\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?)\s*\]?'
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
    parts: List[Tuple[str, str]] = []
    matches = list(TC_RX.finditer(text))
    if not matches:
        return [("", text.strip())]
    for i, m in enumerate(matches):
        tc = normalize_tc(m)
        s = m.end()
        e = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        seg = text[s:e].strip()
        parts.append((tc, seg))
    tail_start = matches[-1].end()
    if tail_start < len(text) and parts:
        extra = text[tail_start:].strip()
        if extra:
            tc, prev = parts[-1]
            parts[-1] = (tc, (prev + " " + extra).strip())
    return parts

def stitch_segments(segments: List[Tuple[str, str]]) -> str:
    out = []
    for tc, body in segments:
        if tc and body:
            out.append(f"{tc} {body}")
        elif tc:
            out.append(tc)
        elif body:
            out.append(body)
    return "\n".join(out).strip()

# ---------- sentence split ----------
ABBR_TAILS = (
    "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sr.", "Jr.", "St.", "vs.",
    "etc.", "e.g.", "i.e.", "p.m.", "a.m."
)
SENT_SPLIT_RX = re.compile(
    r'(?<=[.!?])\s+(?=[A-ZÀ-ÿ\u0590-\u05FF\u0400-\u04FF\u0600-\u06FF0-9])'
)

def split_sentences(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    sents: List[str] = []
    for ln in lines:
        parts = SENT_SPLIT_RX.split(ln)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if sents and sents[-1].endswith(ABBR_TAILS):
                sents[-1] += " " + part
            else:
                sents.append(part)
    return sents

# ---------- numbers protection ----------
NUM_RX = re.compile(
    r"\d{1,2}:\d{2}:\d{2}(?:\.\d{1,3})?"
    r"|\d+\s*%"
    r"|\d+\s*[–\-]\s*\d+"
    r"|\d+\s*[x×]\s*\d+"
    r"|\d+(?:[\.,]\d+)?"
)

def protect_numbers(text: str, placeholders: dict) -> str:
    def repl(m):
        key = f"__NUM{len(placeholders)}__"
        placeholders[key] = m.group(0)
        return key
    return NUM_RX.sub(repl, text)

def restore_numbers(text: str, placeholders: dict) -> str:
    for k, v in placeholders.items():
        text = text.replace(k, v)
    return text

# ---------- batching ----------
def chunks(lst: List[str], n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# ---------- translation core ----------
def translate_sentences(
    sents: List[str],
    tokenizer: AutoTokenizer,
    model: AutoModelForSeq2SeqLM,
    device: str,
    tgt: str,
    batch_size: int,
    max_length: int,
    num_beams: int,
) -> List[str]:
    out: List[str] = []
    for batch in chunks(sents, batch_size):
        nonempty = [s for s in batch if s.strip()]
        if not nonempty:
            out.extend(batch)
            continue
        enc = tokenizer(nonempty, return_tensors="pt", padding=True).to(device)
        gen = model.generate(
            **enc,
            forced_bos_token_id=tokenizer.lang_code_to_id[tgt],
            max_length=max_length,
            num_beams=num_beams,
            no_repeat_ngram_size=2,
        )
        decoded = tokenizer.batch_decode(gen, skip_special_tokens=True)
        it = iter(decoded)
        for s in batch:
            if s.strip():
                out.append(next(it).strip())
            else:
                out.append(s)
    return out

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=False, help="Input text file (default: input.txt)")
    ap.add_argument("--out", dest="out", required=False, help="Output text file (default: translation.txt)")
    ap.add_argument("--src", dest="src", default="auto", help="Source lang: auto|en|he|ar|ru|es|NLLB code")
    ap.add_argument("--tgt", dest="tgt", default="heb_Hebr", help="Target lang: he|en|... or NLLB code")
    ap.add_argument("--batch", dest="batch", type=int, default=16, help="Batch size (sentences per batch)")
    ap.add_argument("--model", dest="model", default="facebook/nllb-200-1.3B")
    ap.add_argument("--max_length", dest="max_length", type=int, default=512)
    ap.add_argument("--beams", dest="beams", type=int, default=8)  # גבוה כברירת מחדל
    args = ap.parse_args()

    # defaults + interactive fallback
    inp = args.inp or "input.txt"
    out = args.out or "translation.txt"
    if not os.path.exists(inp):
        try:
            alt = input(f"Input file '{inp}' not found. Enter path (or Enter to abort): ").strip()
        except EOFError:
            alt = ""
        if alt:
            inp = alt
        if not alt or not os.path.exists(inp):
            print("❌ Input file not found. Aborting.")
            return

    with open(inp, "r", encoding="utf-8") as f:
        text = f.read()

    # resolve languages
    if args.src.strip().lower() == "auto":
        guess = detect_lang_light(text)
        src = {"he": "heb_Hebr", "en": "eng_Latn", "ar": "arb_Arab", "ru": "rus_Cyrl", "es": "spa_Latn"}.get(guess, "eng_Latn")
    else:
        src = map_lang(args.src)
    tgt = map_lang(args.tgt)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[translator] device={device}, model={args.model}, src={src}, tgt={tgt}, batch={args.batch}, beams={args.beams}")

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model)
    model.to(device)
    tokenizer.src_lang = src

    # segment by timecodes
    segments = segment_by_timecodes(text)
    if not any(body.strip() for _, body in segments):
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(stitch_segments(segments))
        print(f"[translator] empty-or-timecode-only input → {out}")
        return

    out_segments: List[Tuple[str, str]] = []
    total = len(segments)
    for i, (tc, body) in enumerate(segments, 1):
        print(f"[translator] segment {i}/{total}")
        sents = split_sentences(body)
        placeholders = {}
        protected = [protect_numbers(s, placeholders) for s in sents] if sents else []
        translated = (
            translate_sentences(
                protected, tokenizer, model, device, tgt,
                batch_size=args.batch, max_length=args.max_length, num_beams=args.beams
            )
            if protected else []
        )
        restored = [restore_numbers(s, placeholders) for s in translated] if translated else []
        new_body = " ".join(restored).strip() if restored else body
        out_segments.append((tc, new_body))

    out_text = stitch_segments(out_segments)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(out_text)
    print(f"[translator] saved: {out}")

if __name__ == "__main__":
    main()
