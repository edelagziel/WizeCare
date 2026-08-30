import os
import glob
import shutil
import subprocess

def convert_wav_to_m4a_ffmpeg(input_wav, output_m4a, bitrate="192k"):
    """
    Convert a single WAV file to M4A format using ffmpeg.
    Args:
        input_wav (str): Path to the input WAV file.
        output_m4a (str): Path to the output M4A file.
        bitrate (str): Audio bitrate for the output file (default: 192k).
    """
    print(f"Starting conversion: {input_wav} -> {output_m4a} (bitrate: {bitrate})")
    command = [
        "ffmpeg", "-y",                # Overwrite output files without asking
        "-i", input_wav,               # Input file
        "-c:a", "aac",                 # Audio codec: AAC
        "-b:a", bitrate,               # Audio bitrate
        output_m4a                     # Output file
    ]
    try:
        subprocess.run(command, check=True)
        print(" Converted:", output_m4a)
    except subprocess.CalledProcessError as e:
        print(f"Error converting {input_wav} to {output_m4a}: {e}")

def convert_and_move_all_wav(folder_wav, folder_m4a, folder_done, bitrate="192k"):
    """
    Convert all WAV files in a folder to M4A format, save them in the output folder,
    and move the original WAV files to a 'done' folder.
    Args:
        folder_wav (str): Path to the folder containing WAV files.
        folder_m4a (str): Path to the folder where M4A files will be saved.
        folder_done (str): Path to the folder where processed WAV files will be moved.
        bitrate (str): Audio bitrate for the output files (default: 192k).
    """
    print(f"Looking for WAV files in: {folder_wav}")
    wav_files = glob.glob(os.path.join(folder_wav, "*.wav"))
    if not wav_files:
        print("No WAV files found in", folder_wav)
        return

    # Ensure the output and done folders exist
    print(f"Ensuring output folder exists: {folder_m4a}")
    os.makedirs(folder_m4a, exist_ok=True)
    print(f"Ensuring done folder exists: {folder_done}")
    os.makedirs(folder_done, exist_ok=True)

    print(f"Found {len(wav_files)} WAV files to process.")
    for idx, wav_file in enumerate(wav_files, 1):
        print(f"\nProcessing file {idx}/{len(wav_files)}: {wav_file}")
        base = os.path.splitext(os.path.basename(wav_file))[0]
        # Save as audio_xx.m4a (e.g., if file is audio_ru_1.wav ⇒ audio_ru.m4a)
        # Extract language code: expects filename like audio_xx_1.wav or audio_xx.wav
        lang_code = base.split("_")[1] if "_" in base else base
        output_m4a = os.path.join(folder_m4a, f"audio_{lang_code}.m4a")

        print(f"Output M4A will be: {output_m4a}")
        convert_wav_to_m4a_ffmpeg(wav_file, output_m4a, bitrate)

        # Move the original WAV file to the 'done' folder
        dest_wav = os.path.join(folder_done, os.path.basename(wav_file))
        shutil.move(wav_file, dest_wav)
        print(f" Moved original WAV to: {dest_wav}")

    print("\nAll files processed.")

if __name__ == "__main__":
    # Entry point for the script
    print("Starting WAV to M4A batch conversion script.")
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Define the relevant folders relative to the script's location
    folder_wav   = os.path.join(base_dir, "WAV")      # Folder containing input WAV files
    folder_m4a   = os.path.join(base_dir, "mp4a")     # Folder to save output M4A files
    folder_done  = os.path.join(base_dir, "wavdone")  # Folder to move processed WAV files

    print(f"Base directory: {base_dir}")
    print(f"WAV folder: {folder_wav}")
    print(f"M4A output folder: {folder_m4a}")
    print(f"WAV done folder: {folder_done}")

    # Start the conversion and moving process
    convert_and_move_all_wav(folder_wav, folder_m4a, folder_done)
    print("Script finished.")
