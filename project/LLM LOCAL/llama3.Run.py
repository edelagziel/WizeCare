import os, re, time, glob, subprocess, requests
from pathlib import Path
from typing import List

INPUT_DIR = r"C:\Users\edenl\OneDrive\Studies\WizeCare\project\LLM LOCAL"
MODEL = "llama3:instruct"
OLLAMA_URL = "http://127.0.0.1:11434"
TIMEOUT = 180

PROMPTS_BY_LANG = {
    "en": ("Rewrite the following English text as clear, professional physical therapy instructions for a patient. "
           "Keep the SAME language (English). Do NOT translate. "
           "Do NOT add or remove any steps or details. Keep the same structure and sentence order. "
           "Preserve EVERY numeral exactly (numbers, counts, sets, reps, ranges, timestamps). "
           "Do NOT introduce any new numbering, bullets, or list markers. "
           "If the input already contains numbering/bullets, keep them as-is; otherwise output plain sentences. "
           "Do NOT add headings, notes, or explanations. Output ONLY the rewritten instructions, no quotes."),
    "he": ("Rewrite the following Hebrew text as clear, professional physical therapy instructions for a patient. "
           "Keep the SAME language (Hebrew). Do NOT translate. "
           "Do NOT add or remove any steps or details. Keep the same structure and sentence order. "
           "Preserve EVERY numeral exactly (numbers, counts, sets, reps, ranges, timestamps). "
           "Do NOT introduce any new numbering, bullets, or list markers. "
           "If the input already contains numbering/bullets, keep them as-is; otherwise output plain sentences. "
           "Do NOT add headings, notes, or explanations. Output ONLY the rewritten instructions, no quotes."),
    "ru": ("Rewrite the following Russian text as clear, professional physical therapy instructions for a patient. "
           "Keep the SAME language (Russian). Do NOT translate. "
           "Do NOT add or remove any steps or details. Keep the same structure and sentence order. "
           "Preserve EVERY numeral exactly (numbers, counts, sets, reps, ranges, timestamps). "
           "Do NOT introduce any new numbering, bullets, or list markers. "
           "If the input already contains numbering/bullets, keep them as-is; otherwise output plain sentences. "
           "Do NOT add headings, notes, or explanations. Output ONLY the rewritten instructions, no quotes."),
    "ar": ("Rewrite the following Arabic text as clear, professional physical therapy instructions for a patient. "
           "Keep the SAME language (Arabic). Do NOT translate. "
           "Do NOT add or remove any steps or details. Keep the same structure and sentence order. "
           "Preserve EVERY numeral exactly (numbers, counts, sets, reps, ranges, timestamps). "
           "Do NOT introduce any new numbering, bullets, or list markers. "
           "If the input already contains numbering/bullets, keep them as-is; otherwise output plain sentences. "
           "Do NOT add headings, notes, or explanations. Output ONLY the rewritten instructions, no quotes."),
    "es": ("Rewrite the following Spanish text as clear, professional physical therapy instructions for a patient. "
           "Keep the SAME language (Spanish). Do NOT translate. "
           "Do NOT add or remove any steps or details. Keep the same structure and sentence order. "
           "Preserve EVERY numeral exactly (numbers, counts, sets, reps, ranges, timestamps). "
           "Do NOT introduce any new numbering, bullets, or list markers. "
           "If the input already contains numbering/bullets, keep them as-is; otherwise output plain sentences. "
           "Do NOT add headings, notes, or explanations. Output ONLY the rewritten instructions, no quotes."),
}

def detect_lang(s: str) -> str:
    if re.search(r"[\u0590-\u05FF]", s): return "he"
    if re.search(r"[\u0400-\u04FF]", s): return "ru"
    if re.search(r"[\u0600-\u06FF]", s): return "ar"
    if re.search(r"\b(el|la|los|las|de|que|para|con|por|y|una|uno|unos|unas)\b", s.lower()): return "es"
    return "en"

def extract_numbers(text: str) -> List[str]:
    pats = [r"\d{1,2}:\d{2}:\d{2}(?:\.\d{1,3})?", r"\d+\s*%", r"\d+\s*[–\-]\s*\d+", r"\d+\s*[x×]\s*\d+", r"\d+(?:[\.,]\d+)?"]
    combined = "|".join(f"({p})" for p in pats)
    seen, out = set(), []
    for m in re.finditer(combined, text):
        tok = m.group(0)
        if tok not in seen: seen.add(tok); out.append(tok)
    return out

LIST_LINE_RX = re.compile(r'^\s*(?:[-*•]|(?:\(?\d+\)?|\d+\.))\s+')
def input_has_list_markers(text: str) -> bool:
    return any(LIST_LINE_RX.search(line) for line in text.splitlines())
def strip_leading_list_markers(text: str) -> str:
    return "\n".join(LIST_LINE_RX.sub("", line) for line in text.splitlines())

def ensure_ollama_running():
    try:
        requests.get(OLLAMA_URL + "/api/tags", timeout=3); return
    except Exception: pass
    try:
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(20):
            time.sleep(0.5)
            try:
                requests.get(OLLAMA_URL + "/api/tags", timeout=1); break
            except Exception: continue
    except FileNotFoundError:
        raise RuntimeError("Ollama not found in PATH. Install from https://ollama.com and reopen terminal.")

def ensure_model():
    try:
        r = requests.get(OLLAMA_URL + "/api/tags", timeout=10)
        if MODEL in (t.get("name") for t in r.json().get("models", [])): return
    except Exception: pass
    subprocess.run(["ollama", "pull", MODEL], check=True)

def chat(prompt: str, user_text: str, temperature: float = 0.2) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {"role":"system","content":
             "You are a careful editor for physical therapy instructions. "
             "Never add or remove steps. Keep sentence order. Preserve ALL numerals exactly. "
             "Do not introduce numbering/bullets if they were not present. "
             "Return ONLY the rewritten instructions; no quotes, no extra commentary."},
            {"role":"user","content":
             f"{prompt}\n\n---\nINPUT:\n{user_text}\n---\nOUTPUT (same sentence order; same language as input; no new numbering):"}
        ],
        "stream": False,
        "options": {"temperature": temperature}
    }
    r = requests.post(OLLAMA_URL + "/api/chat", json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json().get("message", {}).get("content", "").strip()

def latest_txt(dirpath: str) -> Path:
    candidates = sorted(glob.glob(str(Path(dirpath) / "*.txt")), key=os.path.getmtime, reverse=True)
    for fp in candidates:
        name = os.path.basename(fp).lower()
        if name.endswith("_edited.txt"):  continue
        if "prompt" in name:              continue
        try:
            if os.path.getsize(fp) < 40:  continue
        except OSError:                    continue
        return Path(fp)
    raise FileNotFoundError("No suitable .txt found (skipped *_edited.txt and prompt*.txt).")

def rewrite(text: str, max_retries: int = 1) -> str:
    in_lang = detect_lang(text)
    base_prompt = PROMPTS_BY_LANG.get(in_lang, PROMPTS_BY_LANG["en"])
    must_nums = extract_numbers(text)
    had_lists = input_has_list_markers(text)

    out = chat(base_prompt, text)

    if "please provide" in out.lower() or "provide the input" in out.lower():
        out = chat(base_prompt + "\n\nDo not ask for input. Output only the rewritten text.", text, temperature=0.1)

    out_lang = detect_lang(out)
    if out_lang != in_lang:
        force_line = {
            "en":"Do NOT translate; keep the output in English.",
            "he":"Do NOT translate; keep the output in Hebrew.",
            "ru":"Do NOT translate; keep the output in Russian.",
            "ar":"Do NOT translate; keep the output in Arabic.",
            "es":"Do NOT translate; keep the output in Spanish.",
        }.get(in_lang, "Do NOT translate; keep the output in the original language.")
        out = chat(base_prompt + "\n\n" + force_line, text, temperature=0.1)

    if not had_lists and input_has_list_markers(out):
        out = strip_leading_list_markers(out)

    missing = [n for n in must_nums if n not in out]
    tries = 0
    while missing and tries < max_retries:
        prompt2 = (base_prompt + "\n\nIMPORTANT: Include ALL of these numerals EXACTLY as in the source:\n" +
                   ", ".join(missing) + "\nDo NOT introduce numbering/bullets if they were not present.")
        out = chat(prompt2, text, temperature=0.1)
        if not had_lists and input_has_list_markers(out):
            out = strip_leading_list_markers(out)
        missing = [n for n in must_nums if n not in out]
        tries += 1
    return out

# ====== main ======
if __name__ == "__main__":
    ensure_ollama_running()
    ensure_model()
    src_path = latest_txt(INPUT_DIR)
    print(f"Using file: {src_path}")
    text = src_path.read_text(encoding="utf-8").strip()
    result = rewrite(text, max_retries=1)
    out_path = src_path.with_name(src_path.stem + "_edited.txt")
    out_path.write_text(result, encoding="utf-8")
    print(f"\n✔ Done. Wrote: {out_path}\n")
    print(result)
