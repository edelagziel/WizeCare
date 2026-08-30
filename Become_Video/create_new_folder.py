import os
import shutil
import re

# Base directory where all source folders and files are located
BASE_DIR = r'C:\Users\edenl\OneDrive\Studies\WizeCare\Become_Video'

# Prefix for the new video output folders (e.g., video1, video2, ...)
TARGET_PREFIX = 'video'

# Find all directories in BASE_DIR whose names match the pattern 'video' followed by a number (e.g., video1, video2, ...)
dirs = [
    d for d in os.listdir(BASE_DIR)
    if os.path.isdir(os.path.join(BASE_DIR, d)) and re.fullmatch(f"{TARGET_PREFIX}\\d+", d)
]

# Determine the next available number for the new video folder
if dirs:
    # Extract the numeric part from each directory name and find the maximum
    nums = [int(re.findall(r'\d+', d)[0]) for d in dirs]
    next_num = max(nums) + 1
else:
    # If no such directories exist, start with 1
    next_num = 1

# Construct the full path for the new target directory
target_dir = os.path.join(BASE_DIR, f"{TARGET_PREFIX}{next_num}")

# Safety check: abort if the target directory already exists
if os.path.exists(target_dir):
    raise Exception(f"Directory {target_dir} already exists! Aborting.")

# Create the new target directory
os.makedirs(target_dir)

# List of files and directories to copy into the new target directory
FILES_AND_DIRS = [
    "audio_ar", "audio_en", "audio_es", "audio_he", "audio_pt", "audio_ru",
    "high", "low", "medium", "verylow", "master.m3u8", "VideoPage.html"
]

# Copy each file or directory from BASE_DIR to the new target directory
for name in FILES_AND_DIRS:
    src = os.path.join(BASE_DIR, name)
    dst = os.path.join(target_dir, name)
    if os.path.isdir(src):
        # Copy entire directory tree
        shutil.copytree(src, dst)
    elif os.path.isfile(src):
        # Copy single file
        shutil.copy2(src, dst)
    else:
        # Warn if the source does not exist
        print(f"Warning: {src} does not exist!")

print(f"Done! All copied to {target_dir}")
