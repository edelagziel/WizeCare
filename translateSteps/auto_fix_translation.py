import requests

# Model and API configuration
MODEL = "llama3:instruct"
OLLAMA_URL = "http://127.0.0.1:11434"
TIMEOUT = 180  # Timeout for the API request in seconds

def auto_fix_translation(original_translation, review_text, target_lang_code):
    """
    Receives the original translation, a critical review in English, and the target language code.
    Returns an improved/fixed translation ONLY according to explicit corrections in the review.
    """
    # System message instructs the model to only apply explicit corrections from the review
    system_msg = (
        "You are a professional bilingual language editor for physical therapy instructions.\n"
        f"You are given a translation in {target_lang_code} and a critical review in English, pointing out only specific errors and how to fix them.\n"
        "Your job is to apply ONLY the exact changes the review specifies. Do NOT change, rewrite, or reword any part of the translation unless an explicit replacement is provided in the review.\n"
        "If the review provides a correction for a specific phrase, replace ONLY that phrase. Otherwise, keep the original phrase unchanged.\n"
        "If you are unsure about the correction, leave the phrase exactly as in the original translation.\n"
        "Return ONLY the corrected translation in the target language, no comments, and no extra explanations."
    )
    
    # Prompt includes the original translation and the review, and asks for a fixed translation
    prompt = (
        f"---\n"
        f"TRANSLATION ({target_lang_code}):\n{original_translation}\n"
        f"---\n"
        f"REVIEW (English):\n{review_text}\n"
        f"---\n"
        f"FIXED TRANSLATION ({target_lang_code}):"
    )

    # Prepare the payload for the API request
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {"temperature": 0.1}
    }
    # Send the request to the Ollama API
    r = requests.post(OLLAMA_URL + "/api/chat", json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    # Extract the fixed translation from the response
    result = r.json().get("message", {}).get("content", "").strip()
    print("\n=== AUTO-FIXED TRANSLATION ===\n" + result + "\n")
    return result

# Example usage:
if __name__ == "__main__":
    # Example translation and review; you can replace these with any text you want to test
    translation = (
        "هذه هي تعليمات العلاج الطبيعي المعدلة: ابدأ في وضع الجلوس.\n"
        "ضع يديك على جانبك أو خلفك لتدعم ظهرك.\n"
        "أبق مرفقيك مستقيمين ومقفلين\n"
        "اجلس بساقيك مغلقة ومستقيمة أمام جسمك\n"
        "ارفع ساقك اليمنى إلى جانب واحد، وتبقي ركبتيك مستقيمة.\n"
        "إحتفظ بهذا الموقف للحظة\n"
        "حاول أن تجلب ساقك اليسرى نحو ساقك اليمنى\n"
        "انتظر لحظة\n"
        "ثم أعد ساقك اليسرى إلى الوسط، تليها ساقك اليمنى."
    )
    review = (
        "The translation appears to be accurate overall, but there is a critical mistake in the instruction "
        "\"Keep your elbows straight and locked.\" The Arabic translation \"أبق مرفقيك مستقيمين ومقفلين\" mistranslates "
        "the original phrase. Instead of \"locked,\" the correct translation should be \"do not bend\" or \"keep straight\" to convey the same meaning.\n"
        "The rest of the instructions seem to be accurately translated."
    )
    auto_fix_translation(translation, review, "ar")
