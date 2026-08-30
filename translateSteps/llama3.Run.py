import os, re, time, glob, subprocess, requests
from pathlib import Path
from typing import List

# Directory containing input .txt files
INPUT_DIR = r"C:\Users\edenl\OneDrive\Studies\WizeCare\project\LLM LOCAL"
# Name of the Llama3 model to use
MODEL = "llama3:instruct"
# URL for the local Ollama server
OLLAMA_URL = "http://127.0.0.1:11434"
# Timeout for requests to Ollama (in seconds)
TIMEOUT = 180

# Prompts for each supported language, instructing the LLM how to rewrite the text
PROMPTS_BY_LANG = {
    "en": (
        "Rewrite the following English text as clear, professional physical therapy instructions for a patient. "
        "Keep the SAME language (English). Do NOT translate. "
        "Do NOT add or remove any steps or details. Keep the same structure and sentence order. "
        "Preserve EVERY numeral exactly (numbers, counts, sets, reps, ranges, timestamps). "
        "Do NOT introduce any new numbering, bullets, or list markers. "
        "If the input already contains numbering/bullets, keep them as-is; otherwise output plain sentences. "
        "Do NOT add headings, notes, or explanations. Output ONLY the rewritten instructions, no quotes."
    ),
    "he": (
        "Rewrite the following Hebrew text as clear, professional physical therapy instructions for a patient. "
        "Keep the SAME language (Hebrew). Do NOT translate. "
        "Do NOT add or remove any steps or details. Keep the same structure and sentence order. "
        "Preserve EVERY numeral exactly (numbers, counts, sets, reps, ranges, timestamps). "
        "Do NOT introduce any new numbering, bullets, or list markers. "
        "If the input already contains numbering/bullets, keep them as-is; otherwise output plain sentences. "
        "Do NOT add headings, notes, or explanations. Output ONLY the rewritten instructions, no quotes."
    ),
    "ru": (
        "Rewrite the following Russian text as clear, professional physical therapy instructions for a patient. "
        "Keep the SAME language (Russian). Do NOT translate. "
        "Do NOT add or remove any steps or details. Keep the same structure and sentence order. "
        "Preserve EVERY numeral exactly (numbers, counts, sets, reps, ranges, timestamps). "
        "Do NOT introduce any new numbering, bullets, or list markers. "
        "If the input already contains numbering/bullets, keep them as-is; otherwise output plain sentences. "
        "Do NOT add headings, notes, or explanations. Output ONLY the rewritten instructions, no quotes."
    ),
    "ar": (
        "Rewrite the following Arabic text as clear, professional physical therapy instructions for a patient. "
        "Keep the SAME language (Arabic). Do NOT translate. "
        "Do NOT add or remove any steps or details. Keep the same structure and sentence order. "
        "Preserve EVERY numeral exactly (numbers, counts, sets, reps, ranges, timestamps). "
        "Do NOT introduce any new numbering, bullets, or list markers. "
        "If the input already contains numbering/bullets, keep them as-is; otherwise output plain sentences. "
        "Do NOT add headings, notes, or explanations. Output ONLY the rewritten instructions, no quotes."
    ),
    "es": (
        "Rewrite the following Spanish text as clear, professional physical therapy instructions for a patient. "
        "Keep the SAME language (Spanish). Do NOT translate. "
        "Do NOT add or remove any steps or details. Keep the same structure and sentence order. "
        "Preserve EVERY numeral exactly (numbers, counts, sets, reps, ranges, timestamps). "
        "Do NOT introduce any new numbering, bullets, or list markers. "
        "If the input already contains numbering/bullets, keep them as-is; otherwise output plain sentences. "
        "Do NOT add headings, notes, or explanations. Output ONLY the rewritten instructions, no quotes."
    ),
    "fr": (
        "Rewrite the following French text as clear, professional physical therapy instructions for a patient. "
        "Keep the SAME language (French). Do NOT translate. "
        "Do NOT add or remove any steps or details. Keep the same structure and sentence order. "
        "Preserve EVERY numeral exactly (numbers, counts, sets, reps, ranges, timestamps). "
        "Do NOT introduce any new numbering, bullets, or list markers. "
        "If the input already contains numbering/bullets, keep them as-is; otherwise output plain sentences. "
        "Do NOT add headings, notes, or explanations. Output ONLY the rewritten instructions, no quotes."
    ),
    "de": (
        "Rewrite the following German text as clear, professional physical therapy instructions for a patient. "
        "Keep the SAME language (German). Do NOT translate. "
        "Do NOT add or remove any steps or details. Keep the same structure and sentence order. "
        "Preserve EVERY numeral exactly (numbers, counts, sets, reps, ranges, timestamps). "
        "Do NOT introduce any new numbering, bullets, or list markers. "
        "If the input already contains numbering/bullets, keep them as-is; otherwise output plain sentences. "
        "Do NOT add headings, notes, or explanations. Output ONLY the rewritten instructions, no quotes."
    ),
    "pt": (
        "Rewrite the following Portuguese text as clear, professional physical therapy instructions for a patient. "
        "Keep the SAME language (Portuguese). Do NOT translate. "
        "Do NOT add or remove any steps or details. Keep the same structure and sentence order. "
        "Preserve EVERY numeral exactly (numbers, counts, sets, reps, ranges, timestamps). "
        "Do NOT introduce any new numbering, bullets, or list markers. "
        "If the input already contains numbering/bullets, keep them as-is; otherwise output plain sentences. "
        "Do NOT add headings, notes, or explanations. Output ONLY the rewritten instructions, no quotes."
    ),
}

def detect_lang(s: str) -> str:
    """
    Detect the language of the input string using Unicode ranges and common words.
    Returns a short language code (e.g., 'en', 'he', 'ru', etc.).
    """
    if re.search(r"[\u0590-\u05FF]", s):  # Hebrew Unicode block
        return "he"
    if re.search(r"[\u0400-\u04FF]", s):  # Cyrillic (Russian) Unicode block
        return "ru"
    if re.search(r"[\u0600-\u06FF]", s):  # Arabic Unicode block
        return "ar"
    # Simple Spanish word detection
    if re.search(r"\b(el|la|los|las|de|que|para|con|por|y|una|uno|unos|unas)\b", s.lower()):
        return "es"
    return "en"  # Default to English

def extract_numbers(text: str) -> List[str]:
    """
    Extract all unique numerals and numeric patterns from the text.
    Returns a list of unique number strings (e.g., times, percentages, ranges, etc.).
    """
    pats = [
        r"\d{1,2}:\d{2}:\d{2}(?:\.\d{1,3})?",  # time format (e.g., 01:23:45.678)
        r"\d+\s*%",                            # percentages (e.g., 50%)
        r"\d+\s*[–\-]\s*\d+",                  # ranges (e.g., 10-15)
        r"\d+\s*[x×]\s*\d+",                   # sets x reps (e.g., 3x10)
        r"\d+(?:[\.,]\d+)?"                    # plain numbers (e.g., 5, 3.5)
    ]
    combined = "|".join(f"({p})" for p in pats)
    seen, out = set(), []
    for m in re.finditer(combined, text):
        tok = m.group(0)
        if tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out

# Regex to detect list markers at the start of a line (bullets, numbers, etc.)
LIST_LINE_RX = re.compile(r'^\s*(?:[-*•]|(?:\(?\d+\)?|\d+\.))\s+')

def input_has_list_markers(text: str) -> bool:
    """
    Check if any line in the text starts with a list marker (bullet, number, etc.).
    """
    return any(LIST_LINE_RX.search(line) for line in text.splitlines())

def strip_leading_list_markers(text: str) -> str:
    """
    Remove leading list markers from each line in the text.
    """
    return "\n".join(LIST_LINE_RX.sub("", line) for line in text.splitlines())

def ensure_ollama_running():
    """
    Ensure that the Ollama server is running locally.
    If not, attempt to start it. Raise an error if not found.
    """
    try:
        # Try to connect to Ollama server
        requests.get(OLLAMA_URL + "/api/tags", timeout=3)
        return
    except Exception:
        pass
    try:
        # Start Ollama server in the background
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Wait for the server to start (up to 10 seconds)
        for _ in range(20):
            time.sleep(0.5)
            try:
                requests.get(OLLAMA_URL + "/api/tags", timeout=1)
                break
            except Exception:
                continue
    except FileNotFoundError:
        raise RuntimeError("Ollama not found in PATH. Install from https://ollama.com and reopen terminal.")

def ensure_model():
    """
    Ensure that the required Llama3 model is available locally.
    If not, pull it from the Ollama repository.
    """
    try:
        r = requests.get(OLLAMA_URL + "/api/tags", timeout=10)
        if MODEL in (t.get("name") for t in r.json().get("models", [])):
            return
    except Exception:
        pass
    # Pull the model if not present
    subprocess.run(["ollama", "pull", MODEL], check=True)

def chat(prompt: str, user_text: str, temperature: float = 0.2) -> str:
    """
    Send a chat request to the Ollama LLM with the given prompt and user text.
    Returns the model's response as a string.
    """
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a careful editor for physical therapy instructions. "
                    "Never add or remove steps. Keep sentence order. Preserve ALL numerals exactly. "
                    "Do not introduce numbering/bullets if they were not present. "
                    "Return ONLY the rewritten instructions; no quotes, no extra commentary."
                )
            },
            {
                "role": "user",
                "content": (
                    f"{prompt}\n\n---\nINPUT:\n{user_text}\n---\nOUTPUT (same sentence order; same language as input; no new numbering):"
                )
            }
        ],
        "stream": False,
        "options": {"temperature": temperature}
    }
    r = requests.post(OLLAMA_URL + "/api/chat", json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json().get("message", {}).get("content", "").strip()

def latest_txt(dirpath: str) -> Path:
    """
    Find the most recent .txt file in the directory, skipping files ending with '_edited.txt' or containing 'prompt'.
    Returns the Path object for the selected file.
    """
    candidates = sorted(glob.glob(str(Path(dirpath) / "*.txt")), key=os.path.getmtime, reverse=True)
    for fp in candidates:
        name = os.path.basename(fp).lower()
        if name.endswith("_edited.txt"):
            continue
        if "prompt" in name:
            continue
        try:
            if os.path.getsize(fp) < 40:  # Skip very small files
                continue
        except OSError:
            continue
        return Path(fp)
    raise FileNotFoundError("No suitable .txt found (skipped *_edited.txt and prompt*.txt).")

def rewrite(text: str, max_retries: int = 1) -> str:
    """
    Rewrite the input text using the LLM, ensuring all numerals are preserved and no unwanted list markers are added.
    Retries if numerals are missing or output is in the wrong language.
    """
    in_lang = detect_lang(text)
    base_prompt = PROMPTS_BY_LANG.get(in_lang, PROMPTS_BY_LANG["en"])
    must_nums = extract_numbers(text)
    had_lists = input_has_list_markers(text)

    # First attempt to rewrite
    out = chat(base_prompt, text)

    # If the model asks for input, force it to output only the rewritten text
    if "please provide" in out.lower() or "provide the input" in out.lower():
        out = chat(base_prompt + "\n\nDo not ask for input. Output only the rewritten text.", text, temperature=0.1)

    # If the output is in the wrong language, force the correct language
    out_lang = detect_lang(out)
    if out_lang != in_lang:
        force_line = {
            "en": "Do NOT translate; keep the output in English.",
            "he": "Do NOT translate; keep the output in Hebrew.",
            "ru": "Do NOT translate; keep the output in Russian.",
            "ar": "Do NOT translate; keep the output in Arabic.",
            "es": "Do NOT translate; keep the output in Spanish.",
        }.get(in_lang, "Do NOT translate; keep the output in the original language.")
        out = chat(base_prompt + "\n\n" + force_line, text, temperature=0.1)

    # If the input did not have list markers but the output does, remove them
    if not had_lists and input_has_list_markers(out):
        out = strip_leading_list_markers(out)

    # Check for missing numerals and retry if needed
    missing = [n for n in must_nums if n not in out]
    tries = 0
    while missing and tries < max_retries:
        prompt2 = (
            base_prompt + "\n\nIMPORTANT: Include ALL of these numerals EXACTLY as in the source:\n" +
            ", ".join(missing) + "\nDo NOT introduce numbering/bullets if they were not present."
        )
        out = chat(prompt2, text, temperature=0.1)
        if not had_lists and input_has_list_markers(out):
            out = strip_leading_list_markers(out)
        missing = [n for n in must_nums if n not in out]
        tries += 1
    return out

# ====== main entry point ======
if __name__ == "__main__":
    # Ensure Ollama server is running
    ensure_ollama_running()
    # Ensure the required model is available
    ensure_model()
    # Find the latest suitable .txt file in the input directory
    src_path = latest_txt(INPUT_DIR)
    print(f"Using file: {src_path}")
    # Read the input text
    text = src_path.read_text(encoding="utf-8").strip()
    # Rewrite the text using the LLM
    result = rewrite(text, max_retries=1)
    # Write the result to a new file with '_edited.txt' suffix
    out_path = src_path.with_name(src_path.stem + "_edited.txt")
    out_path.write_text(result, encoding="utf-8")
    print(f"\n✔ Done. Wrote: {out_path}\n")
    # Print the rewritten result to the console
    print(result)
