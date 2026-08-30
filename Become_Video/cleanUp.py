import os
import shutil
from pathlib import Path

if os.getenv("WIZECARE_ALLOW_CLEANUP") != "1":
    print("Cleanup is disabled. Set WIZECARE_ALLOW_CLEANUP=1 to run this destructive script.")
    raise SystemExit(0)

# Base directory containing all folders to be cleaned
BASE_DIR = Path(__file__).resolve().parent

# List of directory names to clean inside BASE_DIR
DIRS_TO_CLEAN = [
    "audio_ar", "audio_en", "audio_es", "audio_he", "audio_pt", "audio_ru",
    "done_m4a", "doneVideos", "finiseVideo", "high", "low", "medium", "mp4a", "verylow", "WAV", "wavdone"
]

# Iterate over each directory to clean
for dir_name in DIRS_TO_CLEAN:
    dir_path = BASE_DIR / dir_name
    if dir_path.is_dir():
        # Loop through all items in the directory
        for item_path in dir_path.iterdir():
            try:
                if item_path.is_file() or item_path.is_symlink():
                    # Delete file or symbolic link
                    os.unlink(item_path)
                    print(f"Deleted file: {item_path}")
                elif item_path.is_dir():
                    # Delete subdirectory and all its contents
                    shutil.rmtree(item_path)
                    print(f"Deleted folder: {item_path}")
            except Exception as e:
                # Print error if deletion fails
                print(f"Failed to delete {item_path}. Reason: {e}")
    else:
        # Directory does not exist
        print(f"Directory not found: {dir_path}")

print("All selected folders cleaned successfully!")
