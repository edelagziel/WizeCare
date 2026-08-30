import os
import subprocess
import sys

# Get the absolute path to the directory where this script is located
base_dir = os.path.dirname(os.path.abspath(__file__))

def run_py_script(script_name):
    """
    Helper function to run a Python script by its name in the current directory.
    Prints status before and after execution.
    Raises an exception if the script fails.
    """
    print(f"\n=== Running: {script_name} ===")
    try:
        # Run the script using the full path
        subprocess.run([sys.executable, os.path.join(base_dir, script_name)], check=True)
        print(f"=== Finished: {script_name} ===\n")
    except subprocess.CalledProcessError as e:
        print(f"*** Error running {script_name}: {e}")
        raise

if __name__ == "__main__":
    # Step 1: Convert all WAV files to m4a format.
    # The converted files are saved in the 'mp4a' folder.
    # The original WAV files are moved to the 'wavdone' folder.
    print("Step 1: Convert all WAV files to m4a, save in mp4a, move to wavdone")
    run_py_script("convert_wav_to_m4a.py")
    print("Step 1 completed.\n")

    # Step 2: Convert all m4a files in the 'mp4a' folder to HLS audio format.
    # Output files are placed in folders like audio_xx/audio_xx_high.m3u8.
    # After conversion, the original m4a files are deleted from 'mp4a'.
    print("Step 2: Convert all m4a files in mp4a to HLS audio (audio_xx/audio_xx_high.m3u8), delete from mp4a")
    run_py_script("convert_m4a_to_hls.py")
    print("Step 2 completed.\n")

    # Step 3: Convert all video files in the 'doneVideos' folder to HLS video format.
    # Four quality levels are generated (e.g., video/high/index.m3u8, etc.).
    # After conversion, the original video files are deleted from 'doneVideos'.
    print("Step 3: Convert all video files in doneVideos to HLS video (4 qualities: video/high/index.m3u8 ...), delete from doneVideos")
    run_py_script("convert_video_to_hls.py")
    print("Step 3 completed.\n")

    # Step 4: Generate the main_master.m3u8 playlist, which combines audio and video streams.
    # This is usually handled in convert_m4a_to_hls.py, but you can also use a dedicated script (generate_master.py).
    # To run generate_master.py, uncomment the line below.
    print("Step 4: Generate main_master.m3u8 (combined audio+video)")
    print("Usually this is part of convert_m4a_to_hls.py or you can write a dedicated script (generate_master.py)")
    print("For example, you can run: run_py_script('generate_master.py')")
    # Uncomment the next line to run generate_master.py if needed:
    # run_py_script("generate_master.py")
    print("Step 4 completed.\n")

    # Step 5: Create a new output folder and copy all required files and folders into it.
    # This prepares the final package for deployment or distribution.
    print("Step 5: Create new folder and copy all required files/folders into it")
    run_py_script("create_new_folder.py")
    print("Step 5 completed.\n")

    # Step 6 is destructive, so it is opt-in and disabled for normal/demo runs.
    cleanup_requested = os.getenv("WIZECARE_CLEANUP", "").strip().lower() in {"1", "true", "yes"}
    if cleanup_requested:
        print("Step 6: Clean up selected folders (explicitly enabled)")
        cleanup_env = os.environ.copy()
        cleanup_env["WIZECARE_ALLOW_CLEANUP"] = "1"
        subprocess.run([sys.executable, os.path.join(base_dir, "cleanUp.py")], check=True, env=cleanup_env)
        print("Step 6 completed.\n")
    else:
        print("Step 6 skipped: cleanup is disabled by default. Set WIZECARE_CLEANUP=1 to enable it.\n")

    # All processing steps are finished.
    print("\n=== ALL DONE! ===")
