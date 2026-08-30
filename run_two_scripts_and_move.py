import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Define main directories
ROOT_DIR = Path(__file__).resolve().parent
PIPELINE_DIR = ROOT_DIR / "translateSteps"
BECOME_VIDEO_DIR = ROOT_DIR / "Become_Video"
DONE_ALL_DIR = PIPELINE_DIR / "done_all"
WAV_TARGET = BECOME_VIDEO_DIR / "WAV"
AUDIO_DONE_DIR = PIPELINE_DIR / "audioDone"
SRC_DONE_VIDEOS = PIPELINE_DIR / "doneVideos"
DST_DONE_VIDEOS = BECOME_VIDEO_DIR / "doneVideos"
RUN_PIPELINE_PY = PIPELINE_DIR / "run_pipeline.py"
HLS_PIPELINE_PY = BECOME_VIDEO_DIR / "run_full_hls_pipeline.py"


def move_without_overwrite(source: Path, destination: Path) -> None:
    """Move a file only when the source exists and destination is unused."""
    if not source.is_file():
        raise FileNotFoundError(f"Source file does not exist: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")
    shutil.move(str(source), str(destination))

# Ask the user how many times to run the pipeline
try:
    num_runs = int(input("How many videos would you like to process? "))
except ValueError:
    print("Invalid input. Defaulting to 1.")
    num_runs = 1

for i in range(num_runs):
    print(f"\n=== Processing video {i+1} of {num_runs} ===\n")

    # Step 1
    print("Running run_pipeline.py ...")
    subprocess.run([sys.executable, str(RUN_PIPELINE_PY)], cwd=PIPELINE_DIR, check=True)

    # Step 2
    print("Transferring video files ...")
    DST_DONE_VIDEOS.mkdir(parents=True, exist_ok=True)
    video_files = glob.glob(str(SRC_DONE_VIDEOS / "*.*"))
    if not video_files:
        print("No video files found to move.")
    else:
        for video_file in video_files:
            filename = os.path.basename(video_file)
            dst_path = DST_DONE_VIDEOS / filename
            print(f"Moving {video_file} --> {dst_path}")
            move_without_overwrite(Path(video_file), dst_path)

    # Step 3
    print("Transferring WAV file to done_all as output_en.wav ...")
    DONE_ALL_DIR.mkdir(parents=True, exist_ok=True)
    wav_files = glob.glob(str(AUDIO_DONE_DIR / "*.wav"))
    if not wav_files:
        raise FileNotFoundError("No .wav file found in audioDone directory.")
    src_file = wav_files[0]
    dst_file = DONE_ALL_DIR / "output_en.wav"
    print(f"Moving {src_file} --> {dst_file}")
    move_without_overwrite(Path(src_file), dst_file)

    # Step 4
    print("Moving WAV files to target WAV folder ...")
    WAV_TARGET.mkdir(parents=True, exist_ok=True)
    for wav_file in glob.glob(str(DONE_ALL_DIR / "*.wav")):
        destination = WAV_TARGET / Path(wav_file).name
        print(f"Moving {wav_file} --> {destination}")
        move_without_overwrite(Path(wav_file), destination)

    # Step 5
    print("Running run_full_hls_pipeline.py ...")
    subprocess.run([sys.executable, str(HLS_PIPELINE_PY)], cwd=BECOME_VIDEO_DIR, check=True)

print("\n All done!")
