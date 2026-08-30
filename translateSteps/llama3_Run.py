import os, re, time, glob, subprocess, requests
from pathlib import Path
from typing import List

# Directory containing input .txt files for standalone usage.
INPUT_DIR = r"C:\Users\edenl\OneDrive\Studies\WizeCare\project\LLM LOCAL"
# Model name for Ollama
MODEL = "llama3:instruct"
# Ollama server URL
OLLAMA_URL = "http://127.0.0.1:11434"
# Timeout for requests to Ollama (in seconds)
TIMEOUT = 180

# === Dictionary of critical phrases to ensure consistent translation ===
CRITICAL_PHRASES = {
    "lock your elbows": {
        "ar": "أبق مرفقيك مستقيمتين ومغلقين",
        "he": "השאר את המרפקים נעולים וישרים",
        "ru": "держите локти прямыми и заблокированными",
        "es": "mantén los codos bloqueados וrectos",
        "en": "keep your elbows locked and straight"
    },
    "keep your knees straight": {
        "ar": "أبق רكبتيك مستقيمتين",
        "he": "השאר את הברכיים ישרות",
        "ru": "держите колени прямыми",
        "es": "mantén las rodillas rectas",
        "en": "keep your knees straight"
    },
    # You can add more important phrases here...
}

# Prompts for each supported language
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
    """
    Detect the language of the input string.
    Returns a language code: 'he', 'ru', 'ar', 'es', or 'en'.
    """
    if re.search(r"[\u0590-\u05FF]", s): return "he"  # Hebrew
    if re.search(r"[\u0400-\u04FF]", s): return "ru"  # Russian
    if re.search(r"[\u0600-\u06FF]", s): return "ar"  # Arabic
    if re.search(r"\b(el|la|los|las|de|que|para|con|por|y|una|uno|unos|unas)\b", s.lower()): return "es"  # Spanish
    return "en"  # Default to English

def extract_numbers(text: str) -> List[str]:
    """
    Extract all unique numbers and numeric patterns from the text.
    Returns a list of unique number strings.
    """
    pats = [
        r"\d{1,2}:\d{2}:\d{2}(?:\.\d{1,3})?",  # Timestamps (e.g., 01:23:45.678)
        r"\d+\s*%",                            # Percentages (e.g., 50%)
        r"\d+\s*[–\-]\s*\d+",                  # Ranges (e.g., 10-12)
        r"\d+\s*[x×]\s*\d+",                   # Sets x reps (e.g., 3x10)
        r"\d+(?:[\.,]\d+)?"                    # Numbers (e.g., 10, 10.5)
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

def build_prompt_with_phrases(base_prompt, text, target_lang):
    """
    If any critical phrase is found in the text, add a special instruction to the prompt
    to ensure it is translated consistently.
    Returns the modified prompt and a list of used phrases.
    """
    notes = []
    used_phrases = []
    for phrase, langs in CRITICAL_PHRASES.items():
        found = False
        # Check if the phrase or any of its translations is present in the text
        if phrase.lower() in text.lower():
            found = True
        else:
            for trans in langs.values():
                if trans in text:
                    found = True
                    break
        if found and target_lang in langs:
            notes.append(
                f"If the instruction includes '{phrase}', translate it as: \"{langs[target_lang]}\"."
            )
            used_phrases.append(phrase)
    if notes:
        base_prompt += "\n\n---\nSPECIAL INSTRUCTIONS:\n" + " ".join(notes)
    return base_prompt, used_phrases

def ensure_ollama_running():
    """
    Ensure that the Ollama server is running.
    If not, try to start it.
    """
    try:
        requests.get(OLLAMA_URL + "/api/tags", timeout=3)
        return
    except Exception:
        pass
    try:
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Wait for the server to start
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
    Ensure that the required model is available in Ollama.
    If not, pull it from the repository.
    """
    try:
        r = requests.get(OLLAMA_URL + "/api/tags", timeout=10)
        if MODEL in (t.get("name") for t in r.json().get("models", [])):
            return
    except Exception:
        pass
    subprocess.run(["ollama", "pull", MODEL], check=True)

def chat(prompt: str, user_text: str, temperature: float = 0.2) -> str:
    """
    Send a chat request to the Ollama API with the given prompt and user text.
    Returns the model's response as a string.
    """
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content":
                "You are a careful editor for physical therapy instructions. "
                "Never add or remove steps. Keep sentence order. Preserve ALL numerals exactly. "
                "Do not introduce numbering/bullets if they were not present. "
                "Return ONLY the rewritten instructions; no quotes, no extra commentary."
            },
            {"role": "user", "content":
                f"{prompt}\n\n---\nINPUT:\n{user_text}\n---\nOUTPUT (same sentence order; same language as input; no new numbering):"
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
    Find the most recent .txt file in the directory, skipping files that are edited outputs or prompts.
    Returns the Path object of the selected file.
    """
    candidates = sorted(glob.glob(str(Path(dirpath) / "*.txt")), key=os.path.getmtime, reverse=True)
    for fp in candidates:
        name = os.path.basename(fp).lower()
        if name.endswith("_edited.txt"):
            continue
        if "prompt" in name:
            continue
        try:
            if os.path.getsize(fp) < 40:
                continue
        except OSError:
            continue
        return Path(fp)
    raise FileNotFoundError("No suitable .txt found (skipped *_edited.txt and prompt*.txt).")

def apply_dictionary_replacements(text: str, lang: str) -> str:
    """
    Replace any critical phrase or its translation in the text with the correct translation for the target language.
    Prints a summary of replacements if any were made.
    """
    replaced = []
    for phrase, langs in CRITICAL_PHRASES.items():
        if lang not in langs:
            continue
        # Search for all possible translations for all languages (in case someone inserted the wrong one)
        for possible in list(langs.values()) + [phrase]:
            if possible in text and langs[lang] not in text:
                text = text.replace(possible, langs[lang])
                replaced.append((possible, langs[lang]))
    if replaced:
        print(" Applied dictionary replacements:")
        for src, dst in replaced:
            print(f"  - {src} → {dst}")
    return text

def rewrite(text: str, max_retries: int = 1) -> str:
    """
    Rewrite the input text as clear, professional physical therapy instructions,
    preserving all numerals and structure, and ensuring critical phrases are translated consistently.
    Retries if numerals are missing in the output.
    """
    print(">>> llama3_Run.rewrite CALLED!")
    in_lang = detect_lang(text)
    base_prompt = PROMPTS_BY_LANG.get(in_lang, PROMPTS_BY_LANG["en"])
    base_prompt, used_phrases = build_prompt_with_phrases(base_prompt, text, in_lang)
    if used_phrases:
        print(f" Using dictionary translations for: {', '.join(used_phrases)}")
    must_nums = extract_numbers(text)
    had_lists = input_has_list_markers(text)

    out = chat(base_prompt, text)

    # If the model asks for input, force it to output only the rewritten text
    if "please provide" in out.lower() or "provide the input" in out.lower():
        out = chat(base_prompt + "\n\nDo not ask for input. Output only the rewritten text.", text, temperature=0.1)

    out_lang = detect_lang(out)
    # If the output language is not the same as the input, force the correct language
    if out_lang != in_lang:
        force_line = {
            "en": "Do NOT translate; keep the output in English.",
            "he": "Do NOT translate; keep the output in Hebrew.",
            "ru": "Do NOT translate; keep the output in Russian.",
            "ar": "Do NOT translate; keep the output in Arabic.",
            "es": "Do NOT translate; keep the output in Spanish.",
        }.get(in_lang, "Do NOT translate; keep the output in the original language.")
        out = chat(base_prompt + "\n\n" + force_line, text, temperature=0.1)

    # Remove list markers if the input did not have them but the output does
    if not had_lists and input_has_list_markers(out):
        out = strip_leading_list_markers(out)

    # Ensure all numerals from the input are present in the output
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
    # Automatic replacement according to the critical phrase dictionary
    out = apply_dictionary_replacements(out, in_lang)
    return out

def review_translation_critical_errors(english_text, translated_text, target_lang_code):
    """
    Review the translation for critical errors, especially for key medical actions and terms.
    Returns a short review in English.
    """
    prompt = (
    f"You are a professional bilingual reviewer. "
    f"Compare the following original English instructions and their translation (language code: {target_lang_code}).\n"
    f"First, determine whether the instructions are about physical therapy or about using a device or technology (e.g., Smart TV).\n"
    f"If they are about physical therapy, check for correctness of medical terminology and clarity.\n"
    f"If they are about technology or device usage, check for UI/UX term preservation and proper localization.\n"
    f"In both cases, identify any critical mistakes or mistranslations. "
    f"Return a short review in English (no more than 5 sentences)."
    f"\n\nENGLISH:\n{english_text}\n\nTRANSLATION:\n{translated_text}"
)

    result = chat(prompt, "", temperature=0.1)
    print("\n=== Translation Critical Review ===\n" + result + "\n")
    return result

# ====== main (Standalone usage. If you want to read from a file) ======
if __name__ == "__main__":
    ensure_ollama_running()
    ensure_model()
    src_path = latest_txt(INPUT_DIR)
    print(f"Using file: {src_path}")
    print("Starting eden ...")
    text = src_path.read_text(encoding="utf-8").strip()
    result = rewrite(text, max_retries=1)
    out_path = src_path.with_name(src_path.stem + "_edited.txt")
    out_path.write_text(result, encoding="utf-8")
    print(f"\n Done. Wrote: {out_path}\n")
    print(result)
    # Example for review (assuming you have the original English)
    # english_text = ...  # Insert the English source here
    # review_translation_critical_errors(english_text, result, detect_lang(result))
