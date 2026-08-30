# Import the translation pipeline from HuggingFace transformers
from transformers import pipeline
from lang_config import SUPPORTED_LANGUAGES

# Initialize the translation pipeline with Meta's NLLB-200 model
translator = pipeline("translation", model="facebook/nllb-200-1.3B")

def clean_first_sentence_after_colon(sentences: list[str]) -> list[str]:
    """
    If the first sentence contains a colon (:), remove everything before and including the colon.
    This is useful for removing introductory phrases like "Instruction:" or "Note:".
    Prints the sentence before and after cleaning for debugging purposes.
    """
    if not sentences:
        # If the list is empty, return as is
        return sentences

    first = sentences[0]
    print("[First sentence before cleaning]:", repr(first))

    if ':' in first:
        # If a colon is found, split and keep only the part after the colon
        print("[Colon found in first sentence — splitting...]")
        parts = first.split(':', 1)
        sentences[0] = parts[1].strip()
        print("[First sentence after cleaning]:", repr(sentences[0]))
    else:
        print("[No colon found — no change made]")

    return sentences

def translate_text_nllb(text: str, target_lang_code: str) -> list[str]:
    """
    Translates text from English to the target language specified by a short language code (e.g., 'ar', 'ru', 'he').
    Returns a list of translated sentences.

    Args:
        text (str): The English text to translate.
        target_lang_code (str): The short code for the target language.

    Returns:
        list[str]: List of translated sentences.
    """
    src_lang = "eng_Latn"  # Source language code for English (Latin script)
    # Get the full target language code from the supported languages dictionary, default to Russian if not found
    tgt_lang = SUPPORTED_LANGUAGES.get(target_lang_code.strip().lower(), "rus_Cyrl")

    # Split the input text into sentences using period as a delimiter
    # This is a simple split and may be improved with regex for more accurate sentence splitting
    sentences = [s.strip() for s in text.strip().split('.') if s.strip()]
    translated_sentences = []

    # Translate each sentence individually and collect the results
    for sentence in sentences:
        # Add the period back to each sentence for context
        translated = translator(sentence + ".", src_lang=src_lang, tgt_lang=tgt_lang)
        translated_sentences.append(translated[0]["translation_text"])

    # Optionally clean the first sentence if it contains an introductory phrase with a colon
    translated_sentences = clean_first_sentence_after_colon(translated_sentences)

    return translated_sentences
