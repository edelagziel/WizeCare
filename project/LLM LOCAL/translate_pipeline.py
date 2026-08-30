# translate_pipeline.py — EN -> RU, line-by-line with timecode preservation (click-to-run)

import os, re, json, subprocess, sys
from typing import List
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

# -------- Console UTF-8 (Windows safe) --------
if os.name == "nt":
    try:
        os.system("chcp 65001 >NUL")
    except Exception:
        pass
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

def safe_print(x):
    try:
        print(x)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((str(x) + "\n").encode("utf-8", "replace"))

def log(m): print(f"[*] {m}", flush=True)

# -------- Settings --------
DEFAULT_INFILE = "notes.txt"   # English source (one cue per line, optional timecodes)
DEFAULT_OUTDIR = "out"
SRC = "en"
TGT = "ru"
TOPK = 2                       # NLLB candidates
LLAMA_MODEL = "llama3:instruct"
GLOSSARY_PATH = "glossary.yaml"  # optional, if exists will be loaded as plain text

NLLB_MODEL_NAME = "facebook/nllb-200-1.3B"
LANG2NLLB = {
    "en":"eng_Latn","he":"heb_Hebr","ar":"arb_Arab",
    "ru":"rus_Cyrl","es":"spa_Latn","pt":"por_Latn",
}

# -------- NLLB translator --------
class NLLBTranslator:
    def __init__(self, model_name=NLLB_MODEL_NAME):
        log(f"Loading NLLB model: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)

    def translate_topk(self, text: str, src_lang: str, tgt_lang: str, k: int = 2) -> List[str]:
        src = LANG2NLLB.get(src_lang, "eng_Latn")
        tgt = LANG2NLLB.get(tgt_lang, "eng_Latn")
        self.tokenizer.src_lang = src
        enc = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=1024).to(self.device)
        gen = self.model.generate(
            **enc,
            num_beams=max(4, k),
            num_return_sequences=k,
            forced_bos_token_id=self.tokenizer.lang_code_to_id[tgt],
            length_penalty=1.0,
            early_stopping=True,
        )
        outs = self.tokenizer.batch_decode(gen, skip_special_tokens=True)
        seen, uniq = set(), []
        for o in outs:
            o = o.strip()
            if o and o not in seen:
                seen.add(o); uniq.append(o)
        return uniq

# -------- Ollama (optional) --------
def has_ollama() -> bool:
    from shutil import which
    return which("ollama") is not None

def _run(cmd, input_text=None) -> str:
    r = subprocess.run(cmd, input=(input_text.encode("utf-8") if input_text else None),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{r.stderr.decode('utf-8','ignore')}")
    return r.stdout.decode("utf-8","ignore")

def ollama_run(model: str, prompt: str) -> str:
    return _run(["ollama", "run", model], input_text=prompt)

def _normalize_segment(s: str) -> str:
    # single-line normalization (good for subtitle cues)
    return " ".join((s or "").split())

def _extract_out(s: str) -> str:
    # keep only what's inside <out>...</out>; clean common noise if any leaks
    m = re.search(r"<out>(.*?)</out>", s, flags=re.DOTALL | re.IGNORECASE)
    raw = (m.group(1) if m else s).strip()
    raw = re.sub(r"^```(?:\w+)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    raw = re.sub(r"(?i)^(note:|here is|please provide|source:|target:|glossary:).*$", "", raw).strip()
    return _normalize_segment(raw)

def llama_edit(src: str, tgt: str, llama_model: str, glossary_yaml: str = "") -> str:
    prompt = f"""
You are a bilingual expert editor.
Improve TARGET so it is clear, natural, and terminologically correct — without changing meaning or any numbers/dates/named entities.
Rules:
- Keep structure and tags as-is.
- DO NOT add explanations, notes, or code fences.
- Return ONLY the improved text inside <out>...</out> on a single line.

SOURCE:
{src}

TARGET:
{tgt}

GLOSSARY (YAML, optional):
{glossary_yaml}

Return format:
<out>...</out>
""".strip()
    out = ollama_run(llama_model, prompt)
    return _extract_out(out)

# -------- Helpers --------
TIME_RE = re.compile(
    r'^\s*(\[\s*\d{2}:\d{2}:\d{2}(?:[.,]\d{3})?\s*-->\s*\d{2}:\d{2}:\d{2}(?:[.,]\d{3})?\s*\])\s*(.*)$'
)

def read_lines(path: str) -> List[str]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return [ln.rstrip("\n") for ln in f.readlines()]
    # create example and exit
    ex = [
        "[00:00:00.993 --> 00:00:23.656] 2. Be sure to keep your back straight and stomach tight throughout the whole exercise. 3. Make sure your knees are locked throughout the whole movement.",
        "[00:00:32.313 --> 00:00:47.737] Four Five",
        "[00:00:58.958 --> 00:01:22.448] Nice! Now repeat the same exercise on the other side. One. Two.",
        "[00:01:34.852 --> 00:01:58.797] 3 4 5",
        "[00:02:08.956 --> 00:02:09.968] Excellent!",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(ex) + "\n")
    log(f"Created '{path}'. Paste your EN lines and run again.")
    raise SystemExit(1)

def load_glossary_yaml(path: str) -> str:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def numbers_ok(src: str, tgt: str) -> bool:
    # ignore timecodes when checking numbers
    src_body = TIME_RE.sub(lambda m: m.group(2), src or "")
    tgt_body = TIME_RE.sub(lambda m: m.group(2), tgt or "")
    num = re.compile(r'[-+]?\d+(?:[.,]\d+)?%?')
    from collections import Counter
    return Counter(num.findall(src_body)) == Counter(num.findall(tgt_body))

def is_suspect(src: str, tgt: str) -> str:
    noise = ("here is the improved", "note:", "please provide", "source:", "target:", "glossary:")
    if any(n in (tgt or "").lower() for n in noise):
        return "LLM noise added"
    has_tc = bool(TIME_RE.match(src))
    if has_tc and not TIME_RE.match(tgt):
        return "timecode lost"
    # length drift after removing timecodes
    body = TIME_RE.sub(lambda m: m.group(2), src or "")
    tbody = TIME_RE.sub(lambda m: m.group(2), tgt or "")
    if len(body) > 0 and abs(len(tbody) - len(body)) / len(body) > 0.5:
        return "length drift"
    return ""

# -------- Line-by-line translate --------
def translate_line(nllb: NLLBTranslator, line: str, glossary_yaml: str) -> str:
    if not line.strip():
        return line
    m = TIME_RE.match(line)
    prefix, text = (m.group(1), m.group(2)) if m else ("", line)

    # Step 1: NLLB top-k
    cands = nllb.translate_topk(text, src_lang=SRC, tgt_lang=TGT, k=max(2, TOPK))
    chosen = cands[0] if cands else ""

    # Step 2: optional Llama refine
    if has_ollama():
        refined = llama_edit(text, chosen, llama_model=LLAMA_MODEL, glossary_yaml=glossary_yaml).strip()
    else:
        refined = chosen

    # Step 3: safety checks
    if not numbers_ok(text, refined):
        refined = chosen

    refined = _normalize_segment(refined)
    out_line = f"{prefix} {refined}".strip() if prefix else refined

    # optional debug: flag suspects
    reason = is_suspect(line, out_line)
    if reason:
        safe_print(f"[*] SUSPECT line: {reason}\nSRC: {line}\nTGT: {out_line}\n")

    return out_line

# -------- Main --------
def main():
    os.makedirs(DEFAULT_OUTDIR, exist_ok=True)
    lines = read_lines(DEFAULT_INFILE)
    glossary_yaml = load_glossary_yaml(GLOSSARY_PATH)
    nllb = NLLBTranslator()

    out_lines = [translate_line(nllb, ln, glossary_yaml) for ln in lines]

    base = os.path.splitext(os.path.basename(DEFAULT_INFILE))[0]
    out_path = os.path.join(DEFAULT_OUTDIR, f"{base}.translated.ru.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines) + "\n")

    print("[*] === SOURCE (first 5 lines) ===")
    for l in lines[:5]: safe_print(l)
    print("[*] === FINAL   (first 5 lines) ===")
    for l in out_lines[:5]: safe_print(l)
    print(f"[*] Saved -> {out_path}")

if __name__ == "__main__":
    main()
