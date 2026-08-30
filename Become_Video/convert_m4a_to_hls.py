import os
import glob
import subprocess
import shutil

AUDIO_BITRATE = "192k"

def clean_old_outputs(lang_folder, base_name):
    """
    Remove any leftover HLS segment files and playlist for a given language folder and base name.
    This ensures a clean start for each conversion.
    """
    # Remove all old segment files matching the pattern (e.g., audio_xx_high_*.ts)
    for f in glob.glob(os.path.join(lang_folder, f"{base_name}_high_*.ts")):
        try:
            os.remove(f)
        except Exception:
            pass  # Ignore errors if file does not exist or cannot be removed

    # Remove the old playlist file if it exists (e.g., audio_xx_high.m3u8)
    pl = os.path.join(lang_folder, f"{base_name}_high.m3u8")
    if os.path.exists(pl):
        try:
            os.remove(pl)
        except Exception:
            pass  # Ignore errors if file cannot be removed

def convert_to_hls_audio(input_file, lang_code, output_dir):
    """
    Convert a single M4A audio file to HLS format for a specific language.
    Creates a folder for the language, generates HLS segments and playlist.
    """
    base_name = f"audio_{lang_code}"
    lang_folder = os.path.join(output_dir, base_name)
    print(f"Creating directory for language '{lang_code}': {lang_folder}")
    os.makedirs(lang_folder, exist_ok=True)

    playlist_path = os.path.join(lang_folder, f"{base_name}_high.m3u8")
    segment_pattern = os.path.join(lang_folder, f"{base_name}_high_%03d.ts")

    print(f"Processing: {input_file} ({lang_code})")
    print(f"Output playlist will be: {playlist_path}")
    print(f"Segment pattern: {segment_pattern}")

    # Clean up any old outputs before starting conversion
    clean_old_outputs(lang_folder, base_name)

    # Build the ffmpeg command to convert M4A to HLS (single quality: high)
    command = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-c:a", "aac",
        "-b:a", AUDIO_BITRATE,     # Set audio bitrate
        "-hls_time", "10",         # Segment duration in seconds
        "-start_number", "0",      # Start segment numbering at 0 (must be before hls_segment_filename)
        "-hls_segment_filename", segment_pattern,
        "-hls_list_size", "0",     # Write a complete playlist (VOD) with #EXT-X-ENDLIST
        playlist_path
    ]

    print(f"Running ffmpeg command: {' '.join(command)}")
    subprocess.run(command, check=True)
    print(f"Finished processing {input_file}, playlist created at {playlist_path}")

    return playlist_path

if __name__ == "__main__":
    print("Starting m4a to HLS conversion script.")
    base_folder = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(base_folder, "mp4a")
    output_folder = base_folder
    done_folder = os.path.join(base_folder, "done_m4a")

    # Ensure the 'done_m4a' folder exists for processed files
    os.makedirs(done_folder, exist_ok=True)

    # Find all .m4a files in the input folder
    m4a_files = glob.glob(os.path.join(input_folder, "*.m4a"))
    print(f"Found {len(m4a_files)} .m4a files in '{input_folder}'.")

    if not m4a_files:
        print("No .m4a files found in 'mp4a' folder.")
        exit()

    # Process each .m4a file found
    for filepath in m4a_files:
        filename = os.path.basename(filepath)
        parts = filename.split(".")[0].split("_")
        if len(parts) < 2:
            print(f"Skipping file '{filename}': could not extract language code.")
            continue
        lang_code = parts[1]

        # Convert the m4a file to HLS format for the detected language code
        convert_to_hls_audio(filepath, lang_code, output_folder)

        # Move the processed m4a file to the 'done_m4a' folder
        shutil.move(filepath, os.path.join(done_folder, filename))
        print(f"Moved {filename} to done_m4a/")
