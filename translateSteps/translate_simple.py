# from transformers import pipeline

# # Create a pipeline with Meta's translation model
# translator = pipeline("translation", model="facebook/nllb-200-1.3B")

# # Example text to translate from English to Russian
# # text = "Start in a seated position. Keep your back straight and hands behind you for support."
# text = """
# Start in a seated position on the floor. Keep your back straight and place your hands behind you for support.
# Slowly extend your right leg to the side, keeping the knee straight. Hold the position for a few seconds,
# then try to bring your left leg next to the right one, maintaining balance.
# """

# # Perform the translation
# translated = translator(text, src_lang="eng_Latn", tgt_lang="rus_Cyrl")

# # Print the result
# print(translated[0]["translation_text"])



from audio_transcriber import transcribe_latest_audio
from text_translator import translate_text_nllb, SUPPORTED_LANGUAGES
from llama_cleaner import run_llama_cleaning


def choose_target_language():
    print("\nAvailable languages:")
    for short_code, full_code in SUPPORTED_LANGUAGES.items():
        print(f" - {short_code}: {full_code}")
    print()
    lang = input("Enter target language code (e.g. he, ru, es): ").strip().lower()
    if lang not in SUPPORTED_LANGUAGES:
        print("Unsupported language. Defaulting to 'ru'.")
        lang = "ru"
    return lang


def main():
    # Step 1 – Choose target language
    target_lang = choose_target_language()

    # Step 2 – Transcribe audio
    result = transcribe_latest_audio()
    if result.get("result") != "success":
        print("Transcription failed:", result.get("error"))
        return

    text = result["clean_text"]
    print("\nClean transcription:\n", text)

    # Step 3 – Clean with LLaMA
    cleaned_text = run_llama_cleaning(text)
    print("\nAfter LLaMA cleanup:\n", cleaned_text)

    # Step 4 – Translate to target language
    translated = translate_text_nllb(cleaned_text, target_lang)

    print(f"\nTranslated to {target_lang.upper()}:\n")
    for line in translated:
        print(line)


if __name__ == "__main__":
    main()







# from transformers import pipeline

# # Create pipeline
# translator = pipeline("translation", model="facebook/nllb-200-1.3B")

# # Read content from file
# with open("instructions.txt", "r", encoding="utf-8") as f:
#     text = f.read()

# # Split into sentences by period
# sentences = [s.strip() for s in text.strip().split('.') if s.strip()]

# # Translate each sentence
# for sentence in sentences:
#     full_sentence = sentence + "."
#     translated = translator(full_sentence, src_lang="eng_Latn", tgt_lang="rus_Cyrl")
#     print(translated[0]["translation_text"])
