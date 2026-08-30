import os
import glob
import subprocess
import shutil

QUALITIES = {
    "high":    {"v_bitrate": "3000k", "a_bitrate": "128k", "width": 1920, "height": 1080, "bandwidth": 3200000},
    "med":     {"v_bitrate": "2000k", "a_bitrate": "128k", "width": 1280, "height": 720,  "bandwidth": 2200000},
    "low":     {"v_bitrate": "1200k", "a_bitrate": "96k",  "width": 854,  "height": 480,  "bandwidth": 1300000},
    "verylow": {"v_bitrate": "600k",  "a_bitrate": "64k",  "width": 426,  "height": 240,  "bandwidth": 700000},
}

def convert_to_hls_versions(input_video, output_dir, base_name):
    playlist_files = []

    for quality, conf in QUALITIES.items():
        playlist = os.path.join(output_dir, f"{base_name}_{quality}.m3u8")
        segment_pattern = os.path.join(output_dir, f"{base_name}_{quality}_%03d.ts")
        cmd = [
            "ffmpeg", "-y",
            "-i", input_video,
            "-c:v", "libx264",
            "-b:v", conf["v_bitrate"],
            "-s", f'{conf["width"]}x{conf["height"]}',
            "-c:a", "aac",
            "-b:a", conf["a_bitrate"],
            "-hls_time", "10",
            "-hls_segment_filename", segment_pattern,
            "-preset", "veryfast",
            "-sc_threshold", "0",
            playlist
        ]
        print(f"Encoding {quality} ...")
        subprocess.run(cmd, check=True)
        playlist_files.append((playlist, conf["bandwidth"], quality))

    return playlist_files

def write_master_playlist(output_dir, playlist_files, base_name):
    master_path = os.path.join(output_dir, "main_video_master.m3u8")
    with open(master_path, "w") as f:
        f.write("#EXTM3U\n")
        for playlist, bandwidth, quality in playlist_files:
            uri = os.path.basename(playlist)
            f.write(f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},NAME="{quality}"\n')
            f.write(f"{uri}\n")
    print("Created master playlist:", master_path)

if __name__ == "__main__":
    base_folder = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(base_folder, "doneVideos")
    output_folder = os.path.join(base_folder, "HLS_LANGUAGES", "video")  
    finish_folder = os.path.join(base_folder, "finiseVideo")

    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(finish_folder, exist_ok=True)

    video_files = glob.glob(os.path.join(input_folder, "*.*"))

    for input_video in video_files:
        filename = os.path.basename(input_video)
        name_wo_ext = os.path.splitext(filename)[0]
        print(f"\nProcessing: {filename}")

        playlist_files = convert_to_hls_versions(input_video, output_folder, name_wo_ext)
        write_master_playlist(output_folder, playlist_files, name_wo_ext)

        shutil.move(input_video, os.path.join(finish_folder, filename))
        print(f"Moved {filename} to finiseVideo\n")
