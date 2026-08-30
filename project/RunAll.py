import os
import re
import time
import shutil
import subprocess
from pathlib import Path

# ====== SETTINGS / PATHS ======
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
NODE_SCRIPT   = os.path.join(BASE_DIR, "video-translator-server", "ExtractAudio.js")
AUDIOFILE_DIR = os.path.join(BASE_DIR, "audiofile")       # WhisperX input
TEXTFILES_DIR = os.path.join(BASE_DIR, "TextFiles")       # transcripts + translations + edited
TRANSLATOR    = os.path.join(BASE_DIR, "translatemore.py")# NLLB CLI
LLAMA_DIR     = os.path.join(BASE_DIR, "LLM LOCAL")
LLAMA_SCRIPT  = os.path.join(LLAMA_DIR, "llama3.Run.py")

os.makedirs(AUDIOFILE_DIR, exist_ok=True)
os.makedirs(TEXTFILES_DIR, exist_ok=True)

# ====== USER INPUTS ======
audio_lang = (input("Audio language (he/en/auto)? Default=auto: ").strip() or "auto").lower()
target_lang = input("Target text language (he/en/ar/ru/es). Default=en: ").strip() or "en"
try:
    num_videos = int(input("How many videos to process? (1+): ").strip())
except ValueError:
    num_videos = 1

# ====== HELPERS ======
def timer(label):
    class _T:
        def __enter__(self):
            self.t0 = time.perf_counter()
            print(f"[{label}] started...")
        def __exit__(self, *exc):
            dt = time.perf_counter() - self.t0
            print(f"[{label}] finished in {dt:.1f}s")
    return _T()

def detect_lang_light(s: str) -> str:
    # very light heuristic – מספיק לכאן
    if re.search(r"[\u0590-\u05FF]", s): return "he"
    if re.search(r"[\u0400-\u04FF]", s): return "ru"
    if re.search(r"[\u0600-\u06FF]", s): return "ar"
    if re.search(r"\b(el|la|los|las|de|que|para|con|por|y|una|uno|unos|unas)\b", s.lower()):
        return "es"
    return "en"

def run_node_extract_once(timeout_sec=120):
    """Run ExtractAudio.js once and return absolute path to produced .wav (or None if no video)."""
    if not os.path.isfile(NODE_SCRIPT):
        raise FileNotFoundError(f"Node script not found: {NODE_SCRIPT}")

    try:
        res = subprocess.run(
            ["node", NODE_SCRIPT],
            capture_output=True, text=True, timeout=timeout_sec, cwd=BASE_DIR
        )
    except subprocess.TimeoutExpired:
        print(f"Node/ffmpeg timed out (> {timeout_sec}s)."); raise

    if res.stdout: print(res.stdout.strip())
    if res.returncode != 0:
        if res.stderr: print(res.stderr.strip())
        raise SystemExit("Node script failed.")

    if "No video file found" in res.stdout:
        return None

    m = re.search(r"Audio extracted:\s*([^\r\n]+)", res.stdout)
    if not m: raise SystemExit("Could not parse audio path from Node output.")
    rel_audio = m.group(1).strip()
    abs_audio = os.path.join(BASE_DIR, rel_audio)

    for _ in range(20):
        if os.path.exists(abs_audio): return abs_audio
        time.sleep(0.25)
    raise FileNotFoundError(f"Audio file not found after waiting: {abs_audio}")

def run_translation_cli(input_txt_path: str, src_lang: str, tgt_lang: str, timeout_sec=900) -> str:
    """Call translatemore.py; return path to translated file under TextFiles."""
    if not os.path.isfile(TRANSLATOR):
        raise FileNotFoundError(f"Translator script not found: {TRANSLATOR}")
    stem = Path(input_txt_path).stem
    out_path = os.path.join(TEXTFILES_DIR, f"{stem}_translated_{tgt_lang}.txt")
    cmd = [
        "python", TRANSLATOR,
        "--in", input_txt_path,
        "--src", src_lang,   # 'he' or 'en' (או 'auto' – נתמך בסקריפט למטה)
        "--tgt", tgt_lang,
        "--out", out_path,
        "--batch", "8",
        "--retry", "1"
    ]
    try:
        rc = subprocess.run(cmd, cwd=BASE_DIR, timeout=timeout_sec).returncode
    except subprocess.TimeoutExpired:
        print(f"Translator timed out (> {timeout_sec}s)."); raise
    if rc != 0:
        raise SystemExit(f"Translation failed with exit code {rc}")
    return out_path

def run_llama3_post_edit(translated_path: str, timeout_sec=900) -> str:
    """Copy translated file into LLM LOCAL/, run llama3.Run.py there, then copy _edited back."""
    if not os.path.isfile(LLAMA_SCRIPT):
        raise FileNotFoundError(f"Llama script not found: {LLAMA_SCRIPT}")

    local_in = os.path.join(LLAMA_DIR, os.path.basename(translated_path))
    shutil.copy(translated_path, local_in)

    try:
        rc = subprocess.run(["python", "llama3.Run.py"], cwd=LLAMA_DIR, timeout=timeout_sec).returncode
    except subprocess.TimeoutExpired:
        print(f"Llama post-edit timed out (> {timeout_sec}s)."); raise
    if rc != 0:
        raise SystemExit(f"Llama post-edit failed with exit code {rc}")

    edited_local = os.path.join(LLAMA_DIR, Path(local_in).stem + "_edited.txt")
    if not os.path.exists(edited_local):
        raise FileNotFoundError(f"Edited output not found: {edited_local}")

    final_out = os.path.join(TEXTFILES_DIR, os.path.basename(edited_local))
    shutil.copy(edited_local, final_out)
    return final_out

# ====== MAIN LOOP ======
processed = 0
for i in range(num_videos):
    print(f"\n=== Iteration {i+1}/{num_videos} ===")

    # STEP 1/4: Node extract
    with timer("Step 1/4 Extract (Node)"):
        audio_path = run_node_extract_once()
        if audio_path is None:
            print("No more videos found to process. Stopping."); break

    # copy audio → WhisperX input
    dst_audio_path = os.path.join(AUDIOFILE_DIR, os.path.basename(audio_path))
    shutil.copy(audio_path, dst_audio_path)
    print(f"Copied audio to: {dst_audio_path}")

    # STEP 2/4: WhisperX
    from whisper_pragraf import transcribe_latest_audio
    with timer("Step 2/4 WhisperX"):
        # אם המשתמש ביקש auto – נריץ קיבוע 'auto' (הפונקציה בפנים תתמודד),
        # אחרת נכפה he/en לקיצור זמן
        wl = audio_lang if audio_lang in ("he","en") else "auto"
        tx = transcribe_latest_audio(target_lang=wl, batch_size=16)
    if "error" in tx:
        print("Transcription error:", tx["error"]); continue
    transcript_txt = tx["txt_file"]
    print(f"Transcript saved to: {transcript_txt}")

    # נקרא את הטקסט ונזהה שפה עבור NLLB אם src='auto'
    src_for_nllb = "auto"
    if audio_lang in ("he","en"):
        src_for_nllb = audio_lang
    else:
        text_sample = Path(transcript_txt).read_text(encoding="utf-8")[:2000]
        lang_guess = detect_lang_light(text_sample)
        src_for_nllb = "he" if lang_guess == "he" else "en"
    print(f"NLLB source language set to: {src_for_nllb}")

    # STEP 3/4: NLLB Translation
    with timer(f"Step 3/4 Translate (NLLB) {src_for_nllb}->{target_lang}"):
        translated_path = run_translation_cli(transcript_txt, src_for_nllb, target_lang)
    print(f"Translated file: {translated_path}")

    # STEP 4/4: Ollama post‑edit
    with timer("Step 4/4 Llama3 post‑edit"):
        edited_path = run_llama3_post_edit(translated_path)
    print(f"Edited file: {edited_path}")

    processed += 1

print(f"\nDone. Processed {processed} video(s) out of requested {num_videos}.")
