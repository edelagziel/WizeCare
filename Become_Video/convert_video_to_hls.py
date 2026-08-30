import os
import glob
import subprocess
import shutil

# ===== Quality parameters for HLS renditions =====
# Each quality level defines video bitrate, audio bitrate, and resolution.
QUALITIES = {
    "high":    {"v_bitrate": "3000k", "a_bitrate": "128k", "width": 1920, "height": 1080},
    "medium":  {"v_bitrate": "2000k", "a_bitrate": "128k", "width": 1280, "height": 720},
    "low":     {"v_bitrate": "1200k", "a_bitrate": "96k",  "width": 854,  "height": 480},
    "verylow": {"v_bitrate": "600k",  "a_bitrate": "64k",  "width": 426,  "height": 240},
}

# ===== Utility functions =====
def kbps_to_bps(s: str) -> int:
    """
    Convert a string like '3000k' to 3000000 (bps), or '128k' to 128000.
    If no 'k' suffix, treat as integer bps.
    """
    s = s.strip().lower()
    if s.endswith('k'):
        return int(float(s[:-1]) * 1000)
    return int(s)

def clean_quality_dir(quality_dir: str):
    """
    Remove old playlists and segment files from a quality directory.
    This prevents duplicate segments and numbering issues from previous runs.
    """
    for pat in ("*.m3u8", "segment*.ts"):
        for f in glob.glob(os.path.join(quality_dir, pat)):
            try:
                os.remove(f)
            except Exception:
                pass  # Ignore errors if file does not exist or cannot be removed

def convert_to_hls_versions(input_video: str, base_folder: str):
    """
    Convert a single video file to HLS format in multiple quality levels.
    For each quality, create a subfolder (e.g., 'high', 'medium', etc.) with segments and playlist.
    Also generate a master playlist (index.m3u8) referencing all qualities.
    """
    print(f"Starting HLS conversion for: {input_video}")

    variant_info = []  # Collect info for master playlist (index.m3u8)

    for quality, conf in QUALITIES.items():
        quality_dir = os.path.join(base_folder, quality)
        os.makedirs(quality_dir, exist_ok=True)

        # Clean up any leftover playlists or segments from previous runs
        clean_quality_dir(quality_dir)

        playlist = os.path.join(quality_dir, "index.m3u8")
        # Segment filename pattern includes quality name to avoid mixing segments between qualities
        segment_pattern = os.path.join(quality_dir, f"segment_{quality}_%03d.ts")

        cmd = [
            "ffmpeg", "-y",
            "-i", input_video,
            "-c:v", "libx264",
            "-b:v", conf["v_bitrate"],
            "-s", f'{conf["width"]}x{conf["height"]}',
            "-c:a", "aac",
            "-b:a", conf["a_bitrate"],
            "-hls_time", "10",
            "-start_number", "0",                 # Start segment numbering at 000
            "-hls_segment_filename", segment_pattern,
            "-hls_list_size", "0",                # Write a complete playlist (all segments)
            "-hls_playlist_type", "vod",          # VOD mode, add #EXT-X-ENDLIST
            "-sc_threshold", "0",
            "-preset", "veryfast",
            playlist
        ]

        print(f"Encoding {quality}:\n  {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        print(f"Successfully encoded {quality} quality.")

        # Store info for master playlist: bandwidth (bps), resolution, and relative URI
        bandwidth_bps = kbps_to_bps(conf["v_bitrate"]) + kbps_to_bps(conf["a_bitrate"])
        variant_info.append({
            "quality": quality,
            "bandwidth": bandwidth_bps,
            "resolution": f'{conf["width"]}x{conf["height"]}',
            "uri": os.path.relpath(playlist, base_folder).replace("\\", "/")
        })

    # Create the master playlist (index.m3u8) in the base folder
    master_path = os.path.join(base_folder, "index.m3u8")
    with open(master_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for v in sorted(variant_info, key=lambda x: x["bandwidth"]):
            # BANDWIDTH is in bits per second; RESOLUTION is required by many players
            f.write(f'#EXT-X-STREAM-INF:BANDWIDTH={v["bandwidth"]},RESOLUTION={v["resolution"]},NAME="{v["quality"]}"\n')
            f.write(f'{v["uri"]}\n')
    print(f"Created master playlist: {master_path}")

def main():
    """
    Main function to process all video files in the 'doneVideos' folder.
    For each video, convert to HLS in all qualities, then move the original video to 'finiseVideo'.
    """
    print("Script started.")
    base_folder = os.path.dirname(os.path.abspath(__file__))
    print(f"Base folder: {base_folder}")

    input_folder  = os.path.join(base_folder, "doneVideos")
    finish_folder = os.path.join(base_folder, "finiseVideo")

    # Ensure input and output folders exist
    os.makedirs(input_folder,  exist_ok=True)
    os.makedirs(finish_folder, exist_ok=True)

    # Find all video files in the input folder (any extension)
    video_files = glob.glob(os.path.join(input_folder, "*.*"))
    print(f"Found {len(video_files)} video(s) to process.")

    for input_video in video_files:
        filename = os.path.basename(input_video)
        print(f"\nProcessing: {filename}")

        # Convert the video to HLS in all quality levels
        convert_to_hls_versions(input_video, base_folder)

        # Move the original video to the finish folder after processing
        print(f"Moving {filename} to {finish_folder}")
        shutil.move(input_video, os.path.join(finish_folder, filename))
        print(f"Moved {filename} to finiseVideo\n")

    print("Script finished processing all videos.")

if __name__ == "__main__":
    main()
