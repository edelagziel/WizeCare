import subprocess
import time
from pathlib import Path
import audio_transcriber
import text_translator
import threading

from llama_cleaner import run_llama_cleaning
from lang_config import SUPPORTED_LANGUAGES
from llama3_Run import rewrite, review_translation_critical_errors
from auto_fix_translation import auto_fix_translation
from azure_tts import render_by_timestamps
from build_timed_script import map_text_to_timestamps_anylang
from find_matching_file import find_matching_number_in_hebvideo
from pipeline_config import DONE_ALL_DIR, LANGUAGE, NUM_VIDEOS, RUN_MODE, TEXT_DIR

def timed_input(prompt, timeout=50, default="all"):
    result = [default]
    def read_input():
        try:
            result[0] = input(prompt)
        except EOFError:
            pass
    thread = threading.Thread(target=read_input)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        print(f"\n No input after {timeout} seconds. Defaulting to '{default}'.")
    return result[0].strip().lower()

def extract_audio_with_node():
    """
    Extracts audio from the latest video using a Node.js script.
    """
    print("\nStep 0: Extracting audio from the latest video using Node.js...\n")
    t0 = time.time()
    result = subprocess.run(
        ['node', 'extract_audio.js'],
        cwd=TEXT_DIR.parent,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print("Audio extraction failed:", result.stderr)
        raise RuntimeError("Audio extraction failed")
    print(f" Audio extraction step complete. ({time.time() - t0:.1f} sec)\n")

def run_pipeline(lang_code: str, run_index: int, total_runs: int, cleaned_text: str):
    """
    Runs the main translation and audio generation pipeline for a single language.
    """
    total_start = time.time()
    print(f"\n========== Run {run_index} of {total_runs} | Language: {lang_code.upper()} ==========\n")

    # Step 3 – Translation
    print(f"Step 3: Translating to {lang_code.upper()}...\n")
    t3 = time.time()
    translated = text_translator.translate_text_nllb(cleaned_text, lang_code)
    for line in translated:
        print(line)
    print(f" Translation done. ({time.time() - t3:.1f} sec)\n")

    # Step 4 – LLaMA3 Refinement
    print(f"Step 4: LLaMA3 Refinement ({lang_code.upper()})...\n")
    t4 = time.time()
    translated_text = "\n".join(translated) if isinstance(translated, list) else str(translated)
    final_text = rewrite(translated_text)
    print(final_text)
    print(f" LLaMA3 rewrite done. ({time.time() - t4:.1f} sec)\n")

    # Step 5 – Translation Critical Review
    print("Step 5: Translation Critical Review...\n")
    t5 = time.time()
    review_result = review_translation_critical_errors(cleaned_text, final_text, lang_code)
    print(f" Review done. ({time.time() - t5:.1f} sec)\n")

    # Step 6 – Auto-fix Translation
    print("Step 6: Auto-fix Translation...\n")
    t6 = time.time()
    fixed_translation = auto_fix_translation(final_text, review_result, lang_code)
    print(fixed_translation)
    print(f" Auto-fix done. ({time.time() - t6:.1f} sec)\n")

    # Step 6.5 – Map translation to timestamps
    print("Step 6.5: Mapping translation to timestamps...\n")
    # NOTE: The import below is redundant if already imported at the top.
    from build_timed_script import map_text_to_timestamps_anylang
    eng_timestamps_file = TEXT_DIR / "EngAudio.txt"
    output_lines_file = TEXT_DIR / "TimedText.txt"

    map_text_to_timestamps_anylang(
        fixed_translation,        # The improved translation after all processing
        eng_timestamps_file,      # English timestamps file
        str(output_lines_file)    # Output file for mapped lines
    )
    print(f" Mapping done, output: {output_lines_file}\n")

    # Step 7 – Create audio by timestamps
    print("Step 7: Creating Audio by Timestamps...\n")
    t7 = time.time()
    timed_txt = TEXT_DIR / "TimedText.txt"
    output_wav = DONE_ALL_DIR / f"output_{lang_code}_{run_index}.wav"
    if output_wav.exists():
        raise FileExistsError(f"Refusing to overwrite existing TTS output: {output_wav}")
    render_by_timestamps(str(timed_txt), str(output_wav), lang_code)
    print(f"Audio saved to: {output_wav} ({time.time() - t7:.1f} sec)")

def main():
    """
    Main entry point for the pipeline. Handles user input and processes videos.
    """
    num_videos = NUM_VIDEOS

    mode = RUN_MODE or timed_input("\nRun mode? Type 'all' for all languages, or 'manual' for a single one: ", timeout=15, default="all")
    if mode not in ["all", "manual"]:
        print("Invalid choice. Defaulting to manual.")
        mode = "manual"

    for video_index in range(num_videos):
        print(f"\n=== Processing video {video_index + 1} of {num_videos} ===")
        
        # Step 0 – Convert video to audio
        extract_audio_with_node()

        # Step 0.5 – Find matching Hebrew file
        success, number, heb_filename = find_matching_number_in_hebvideo()
        if not success:
            print("No matching file found in HebVideo. Skipping this video.")
            continue

        print(f"Matching file found in HebVideo: {heb_filename}, extracting audio...\n")
        heb_proc = subprocess.run(['node', 'extract_Heb_audio.js', heb_filename], capture_output=True, text=True)
        print(heb_proc.stdout)
        if heb_proc.returncode != 0:
            print("Audio extraction for Hebrew video failed:", heb_proc.stderr)
            continue

        # Step 1 – Transcription
        print("\nStep 1: Transcription...\n")
        t1 = time.time()
        result = audio_transcriber.transcribe_latest_audio()
        if result.get("result") != "success":
            print("Transcription failed:", result.get("error"))
            continue
        original_text = result["clean_text"]
        print(original_text)
        print(f" Transcription done. ({time.time() - t1:.1f} sec)\n")

        # Step 2 – LLaMA Cleanup
        print("Step 2: LLaMA Cleanup...\n")
        t2 = time.time()
        cleaned_text = run_llama_cleaning(original_text)
        print(cleaned_text)
        print(f" LLaMA cleanup done. ({time.time() - t2:.1f} sec)\n")

        if mode == "manual":
            # Manual mode: ask user for language
            print("\nAvailable languages:")
            for code, name in SUPPORTED_LANGUAGES.items():
                print(f" - {code}: {name}")
            lang_code = LANGUAGE or input("Enter language code: ").strip().lower()
            if lang_code not in SUPPORTED_LANGUAGES:
                print("Unsupported language. Using 'ru'.")
                lang_code = "ru"

            run_pipeline(lang_code, run_index=1, total_runs=1, cleaned_text=cleaned_text)

        elif mode == "all":
            # All mode: process all supported languages
            for lang_code in SUPPORTED_LANGUAGES:
                run_pipeline(lang_code, run_index=video_index + 1, total_runs=num_videos, cleaned_text=cleaned_text)

if __name__ == "__main__":
    main()
