# RunAll.py
import os
import re
import time
import shutil
import subprocess
from pathlib import Path

# ====== SETTINGS / PATHS ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NODE_SCRIPT = os.path.join(BASE_DIR, "video-translator-server", "ExtractAudio.js")
AUDIOFILE_DIR = os.path.join(BASE_DIR, "audiofile")               # WhisperX input dir
TEXTFILES_DIR = os.path.join(BASE_DIR, "TextFiles")               # transcripts + translations
TRANSLATOR = os.path.join(BASE_DIR, "translatemore.py")           # CLI translator (NLLB)

os.makedirs(AUDIOFILE_DIR, exist_ok=True)
os.makedirs(TEXTFILES_DIR, exist_ok=True)

# ====== USER INPUTS ======
target_lang = input("Enter target language (e.g., he, en, ar, ru, es). Default=en: ").strip() or "en"
try:
    num_videos = int(input("How many videos to process? (1+): ").strip())
except ValueError:
    num_videos = 1

# ====== HELPERS ======
def timer(label):
    """simple context-like timer"""
    class _T:
        def __enter__(self):
            self.t0 = time.perf_counter()
            print(f"[{label}] started...")
        def __exit__(self, *exc):
            dt = time.perf_counter() - self.t0
            print(f"[{label}] finished in {dt:.1f}s")
    return _T()

def run_node_extract_once(timeout_sec=120):
    """
    Runs ExtractAudio.js once.
    Returns absolute path to produced .wav or None if 'No video file found'.
    Raises on errors/timeout.
    """
    if not os.path.isfile(NODE_SCRIPT):
        raise FileNotFoundError(f"Node script not found: {NODE_SCRIPT}")

    try:
        res = subprocess.run(
            ["node", NODE_SCRIPT],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=BASE_DIR
        )
    except subprocess.TimeoutExpired:
        print(f"Node/ffmpeg timed out (> {timeout_sec}s).")
        raise

    if res.stdout:
        print(res.stdout.strip())
    if res.returncode != 0:
        if res.stderr:
            print(res.stderr.strip())
        raise SystemExit("Node script failed.")

    if "No video file found" in res.stdout:
        return None

    m = re.search(r"Audio extracted:\s*([^\r\n]+)", res.stdout)
    if not m:
        raise SystemExit("Could not parse audio path from Node output.")
    rel_audio = m.group(1).strip()  # e.g. 'output\\TryAudio.wav'
    abs_audio = os.path.join(BASE_DIR, rel_audio)

    # wait until file exists (in case ffmpeg flush is delayed)
    for _ in range(20):
        if os.path.exists(abs_audio):
            return abs_audio
        time.sleep(0.25)

    raise FileNotFoundError(f"Audio file not found after waiting: {abs_audio}")

def run_translation_cli(input_txt_path: str, tgt_lang: str, timeout_sec=600) -> str:
    """
    Calls translatemore.py as a CLI.
    Saves to TextFiles/<stem>_translated_<tgt>.txt and returns that path.
    """
    if not os.path.isfile(TRANSLATOR):
        raise FileNotFoundError(f"Translator script not found: {TRANSLATOR}")

    stem = Path(input_txt_path).stem
    out_path = os.path.join(TEXTFILES_DIR, f"{stem}_translated_{tgt_lang}.txt")
    cmd = [
        "python", TRANSLATOR,
        "--in", input_txt_path,
        "--src", "en",            # אם המקור לא אנגלית—שנה כאן או הפוך ל־input מהמשתמש
        "--tgt", tgt_lang,
        "--out", out_path,
        "--batch", "8"
    ]
    # inherit stdout so you see translator heartbeat; enforce timeout
    try:
        rc = subprocess.run(cmd, cwd=BASE_DIR, timeout=timeout_sec).returncode
    except subprocess.TimeoutExpired:
        print(f"Translator timed out (> {timeout_sec}s).")
        raise
    if rc != 0:
        raise SystemExit(f"Translation failed with exit code {rc}")
    return out_path

# ====== MAIN LOOP ======
processed = 0

for i in range(num_videos):
    print(f"\n=== Iteration {i+1}/{num_videos} ===")

    # STEP 1: Node extract
    with timer("Step 1/3 Extract (Node)"):
        audio_path = run_node_extract_once()
        if audio_path is None:
            print("No more videos found to process. Stopping.")
            break

    # copy audio to WhisperX input dir
    dst_audio_path = os.path.join(AUDIOFILE_DIR, os.path.basename(audio_path))
    shutil.copy(audio_path, dst_audio_path)
    print(f"Copied audio to: {dst_audio_path}")

    # STEP 2: WhisperX transcription (import your function)
    from whisper_pragraf import transcribe_latest_audio  # assumed in project root
    with timer("Step 2/3 WhisperX"):
        tx = transcribe_latest_audio()
    if "error" in tx:
        print("Transcription error:", tx["error"])
        continue
    transcript_txt = tx["txt_file"]
    print(f"Transcript saved to: {transcript_txt}")

    # STEP 3: Translation
    with timer(f"Step 3/3 Translate -> {target_lang}"):
        translated_path = run_translation_cli(transcript_txt, target_lang)
    print(f"Translated file: {translated_path}")

    processed += 1

print(f"\nDone. Processed {processed} video(s) out of requested {num_videos}.")
