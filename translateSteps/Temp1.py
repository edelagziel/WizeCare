import subprocess
import time
import audio_transcriber
import text_translator
from llama_cleaner import run_llama_cleaning
from lang_config import SUPPORTED_LANGUAGES
from llama3_Run import rewrite, review_translation_critical_errors
from auto_fix_translation import auto_fix_translation
from azure_tts import tts

def extract_audio_with_node():
    print("\nStep 0: Extracting audio from the latest video using Node.js...\n")
    t0 = time.time()
    result = subprocess.run(['node', 'extract_audio.js'], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("Audio extraction failed:", result.stderr)
        raise RuntimeError("Audio extraction failed")
    print(f" Audio extraction step complete. ({time.time() - t0:.1f} sec)\n")

def run_pipeline(lang_code: str, run_index: int, total_runs: int, cleaned_text: str):
    total_start = time.time()
    print(f"\n========== Run {run_index} of {total_runs} | Language: {lang_code.upper()} ==========\n")

    # שלב 3 – תרגום
    print(f"Step 3: Translating to {lang_code.upper()}...\n")
    t3 = time.time()
    translated = text_translator.translate_text_nllb(cleaned_text, lang_code)
    for line in translated:
        print(line)
    print(f" Translation done. ({time.time() - t3:.1f} sec)\n")

    # שלב 4 – שיפור עם LLaMA3
    print(f"Step 4: LLaMA3 Refinement ({lang_code.upper()})...\n")
    t4 = time.time()
    translated_text = "\n".join(translated) if isinstance(translated, list) else str(translated)
    final_text = rewrite(translated_text)
    print(final_text)
    print(f" LLaMA3 rewrite done. ({time.time() - t4:.1f} sec)\n")

    # שלב 5 – ביקורת תרגום
    print("Step 5: Translation Critical Review...\n")
    t5 = time.time()
    review_result = review_translation_critical_errors(cleaned_text, final_text, lang_code)
    print(f" Review done. ({time.time() - t5:.1f} sec)\n")

    # שלב 6 – תיקון אוטומטי
    print("Step 6: Auto-fix Translation...\n")
    t6 = time.time()
    fixed_translation = auto_fix_translation(final_text, review_result, lang_code)
    print(fixed_translation)
    print(f" Auto-fix done. ({time.time() - t6:.1f} sec)\n")

    # שלב 7 – יצירת אודיו
    print("Step 7: Creating Audio...\n")
    t7 = time.time()
    output_file = f"done_all/output_{lang_code}_{run_index}.wav"
    tts(fixed_translation, lang_code, to_file=output_file, use_ssml=True, slow=True)
    print(f"Audio saved to: {output_file} ({time.time() - t7:.1f} sec)")

    print(f"\n Total pipeline time: {time.time() - total_start:.1f} seconds")

def main():
    try:
        num_videos = int(input("How many videos would you like to process? "))
    except ValueError:
        print("Invalid input. Processing 1 video.")
        num_videos = 1

    mode = input("\nRun mode? Type 'all' for all languages, or 'manual' for a single one: ").strip().lower()
    if mode not in ["all", "manual"]:
        print("Invalid choice. Defaulting to manual.")
        mode = "manual"

    for video_index in range(num_videos):
        print(f"\n=== Processing video {video_index + 1} of {num_videos} ===")
        
        # שלב 0 – המרת וידאו לאודיו
        extract_audio_with_node()

        # שלב 1 – תמלול
        print("\nStep 1: Transcription...\n")
        t1 = time.time()
        result = audio_transcriber.transcribe_latest_audio()
        if result.get("result") != "success":
            print("Transcription failed:", result.get("error"))
            continue
        original_text = result["clean_text"]
        print(original_text)
        print(f" Transcription done. ({time.time() - t1:.1f} sec)\n")

        # שלב 2 – ניקוי
        print("Step 2: LLaMA Cleanup...\n")
        t2 = time.time()
        cleaned_text = run_llama_cleaning(original_text)
        print(cleaned_text)
        print(f" LLaMA cleanup done. ({time.time() - t2:.1f} sec)\n")

        if mode == "manual":
            print("\nAvailable languages:")
            for code, name in SUPPORTED_LANGUAGES.items():
                print(f" - {code}: {name}")
            lang_code = input("Enter language code: ").strip().lower()
            if lang_code not in SUPPORTED_LANGUAGES:
                print("Unsupported language. Using 'ru'.")
                lang_code = "ru"

            run_pipeline(lang_code, run_index=1, total_runs=1, cleaned_text=cleaned_text)

        elif mode == "all":
            for lang_code in SUPPORTED_LANGUAGES:
                run_pipeline(lang_code, run_index=video_index + 1, total_runs=num_videos, cleaned_text=cleaned_text)

if __name__ == "__main__":
    main()
