import subprocess
import time
import os
import shutil

def extract_audio_with_node():
    """
    Extracts audio from the latest video using a Node.js script.
    """
    print("\nStep 0: Extracting audio from the latest video using Node.js...\n")
    t0 = time.time()
    # Run the Node.js script to extract audio
    result = subprocess.run(['node', 'extract_audio.js'], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        # If the Node.js script failed, print the error and raise an exception
        print("Audio extraction failed:", result.stderr)
        raise RuntimeError("Audio extraction failed")
    print(f" Audio extraction step complete. ({time.time() - t0:.1f} sec)\n")

def move_latest_audio_to_doneall():
    """
    Moves the most recently modified audio file from the 'audioDone' directory
    to the 'doneAll' directory.
    """
    # Define source and destination directories
    audio_done_dir = r'C:\Users\edenl\OneDrive\Studies\WizeCare\translateSteps\audioDone'
    doneall_dir = r'C:\Users\edenl\OneDrive\Studies\WizeCare\translateSteps\doneAll'

    # Ensure the destination directory exists
    os.makedirs(doneall_dir, exist_ok=True)  

    # List all files in the source directory
    files = [os.path.join(audio_done_dir, f) for f in os.listdir(audio_done_dir) if os.path.isfile(os.path.join(audio_done_dir, f))]
    if not files:
        print("No audio files found in audioDone directory.")
        return

    # Find the most recently modified file
    latest_file = max(files, key=os.path.getmtime)
    dest_file = os.path.join(doneall_dir, os.path.basename(latest_file))

    # Move the latest file to the destination directory
    shutil.move(latest_file, dest_file)
    print(f"Moved latest audio file: {os.path.basename(latest_file)} --> doneAll")

if __name__ == "__main__":
    # Step 0: Extract audio from the latest video
    extract_audio_with_node()
    # Step 1: Move the latest audio file to the doneAll directory
    move_latest_audio_to_doneall()
