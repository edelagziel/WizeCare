import re

# ===== Part 1: Number conversion =====

_UNDER_20 = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen"
]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

def int_to_words(n: int) -> str:
    if n < 0:
        return "minus " + int_to_words(-n)
    if n < 20:
        return _UNDER_20[n]
    if n < 100:
        t, r = divmod(n, 10)
        return _TENS[t] + ("" if r == 0 else " " + _UNDER_20[r])
    if n == 100:
        return "one hundred"
    return str(n)  # fallback

# Build vocabulary dynamically (0–100)
_NUMBER_WORDS = {int_to_words(i) for i in range(0, 101)}
_NUMBER_WORDS.discard("")
_NUMBER_REGEX = re.compile(r"\b(" + "|".join(sorted(_NUMBER_WORDS, key=len, reverse=True)) + r")\b", re.IGNORECASE)

# ===== Part 2: Regex patterns =====

_DECIMAL_PATTERN = re.compile(r"\b\d+\.\d+\b")
_NUMBER_SEQUENCE = re.compile(r"(?<!\w)(\d+(?:\s+\d+)+)(?!\w)")
_STANDALONE_INT = re.compile(r"\b\d+\b")

def protect_spans(text: str, patterns):
    protected = []
    marks = []
    tmp = text
    for pat in patterns:
        for m in pat.finditer(text):
            token = text[m.start():m.end()]
            key = f"__PROT{len(protected)}__"
            protected.append(token)
            marks.append((key, token))
            tmp = tmp.replace(token, key, 1)
    return tmp, marks

def unprotect_spans(text: str, marks):
    out = text
    for key, token in marks:
        out = out.replace(key, token)
    return out

# ===== Part 3: Conversion logic =====

def digits_to_english_words(text: str) -> str:
    tmp, marks = protect_spans(text, [_DECIMAL_PATTERN])

    # Replace number sequences like "1 2 3 4"
    def _seq_sub(m):
        return " ".join(int_to_words(int(x)) for x in m.group(1).split())
    tmp = _NUMBER_SEQUENCE.sub(_seq_sub, tmp)

    # Replace standalone numbers
    def _int_sub(m):
        return int_to_words(int(m.group(0)))
    tmp = _STANDALONE_INT.sub(_int_sub, tmp)

    return unprotect_spans(tmp, marks)

# ===== Part 4: Cleanup logic (stub without LLaMA) =====

def run_llama_cleaning(original_text: str) -> str:
    """
    Converts digits to words and simulates cleanup.
    In real pipeline, this would call LLaMA (Ollama client).
    """
    converted_text = digits_to_english_words(original_text)

    # Stub: just replace "stomach closed" -> "stomach tight"
    cleaned = converted_text.replace("stomach closed", "stomach tight")

    # Safety: if numbers disappeared, fallback
    number_words = set(_NUMBER_REGEX.findall(converted_text))
    if number_words:
        missing = [w for w in number_words if w.lower() not in cleaned.lower()]
        if missing:
            print(f"⚠️ Removed number words {missing} — restoring safe version.")
            return converted_text

    return cleaned.strip()

# ===== Part 5: Test runner =====

if __name__ == "__main__":
    test_text = """Make four rows on each side. 1 2
Keep your back straight and your stomach closed during the exercise. 3. Keep in mind that the hips remain straight during the exercise. 4.
5 Great! Do it on the other side in the same way 1
2 3 4
5 Excellent!
"""

    result = run_llama_cleaning(test_text)
    print("\n=== Cleaned Output ===\n")
    print(result)