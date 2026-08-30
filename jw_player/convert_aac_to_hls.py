import os
import glob
import subprocess
import shutil

# הגדרות איכות – שם, ביטרייט, רוחב פס
QUALITIES = {
    "high":    {"bitrate": "192k", "bandwidth": 192000},
    "med":     {"bitrate": "128k", "bandwidth": 128000},
    "low":     {"bitrate": "64k",  "bandwidth": 64000},
    "verylow": {"bitrate": "32k",  "bandwidth": 32000},
}

def convert_to_hls_versions(input_file, lang_code, output_dir):
    base_name = f"audio_{lang_code}"
    lang_folder = os.path.join(output_dir, base_name)
    os.makedirs(lang_folder, exist_ok=True)

    print(f"Processing: {input_file}  {lang_code}")

    # צור את 4 רמות האיכות
    for quality, config in QUALITIES.items():
        playlist_path = os.path.join(lang_folder, f"{base_name}_{quality}.m3u8")
        segment_pattern = os.path.join(lang_folder, f"{base_name}_{quality}_%03d.ts")

        command = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-c:a", "aac",
            "-b:a", config["bitrate"],
            "-hls_time", "10",
            "-hls_segment_filename", segment_pattern,
            playlist_path
        ]
        print(f"   {quality} ({config['bitrate']})")
        subprocess.run(command, check=True)

    # צור קובץ master לכל שפה
    master_path = os.path.join(lang_folder, f"{base_name}_master.m3u8")
    with open(master_path, "w") as f:
        f.write("#EXTM3U\n")
        for quality, config in QUALITIES.items():
            uri = f"{base_name}_{quality}.m3u8"
            f.write(f'#EXT-X-STREAM-INF:BANDWIDTH={config["bandwidth"]},NAME="{quality}"\n')
            f.write(f"{uri}\n")
    return master_path, lang_code


def generate_main_master(output_dir, per_language_masters, video_m3u8_path):
    main_path = os.path.join(output_dir, "main_master.m3u8")
    with open(main_path, "w") as f:
        f.write("#EXTM3U\n\n")

        # הגדרות קבוצות אודיו
        for master_path, lang in per_language_masters:
            group_id = f"audio_{lang}"
            name = lang.capitalize()
            uri = os.path.relpath(master_path, output_dir).replace("\\", "/")
            f.write(f'#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="{group_id}",NAME="{name}",LANGUAGE="{lang}",DEFAULT=NO,AUTOSELECT=YES,URI="{uri}"\n')

        # מסלול וידאו (מהתיקייה החדשה)
        video_uri = os.path.relpath(video_m3u8_path, output_dir).replace("\\", "/")
        for _, lang in per_language_masters:
            group_id = f"audio_{lang}"
            f.write(f'#EXT-X-STREAM-INF:BANDWIDTH=256000,AUDIO="{group_id}"\n')
            f.write(f"{video_uri}\n")

    print(" Created main_master.m3u8")


if __name__ == "__main__":
    base_folder = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(base_folder, "mp4a")
    output_folder = os.path.join(base_folder, "HLS_LANGUAGES")
    done_folder = os.path.join(base_folder, "done_m4a")

    #  עדכון – נתיב לקובץ וידאו נמצא עכשיו בתוך HLS_LANGUAGES/video
    video_folder = os.path.join(base_folder, "HLS_LANGUAGES", "video")
    VIDEO_M3U8_PATH = os.path.join(video_folder, "main_video_master.m3u8")

    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(done_folder, exist_ok=True)

    m4a_files = glob.glob(os.path.join(input_folder, "*.m4a"))

    if not m4a_files:
        print(" No audio_*.m4a files found in 'mp4a' folder.")
        exit()

    per_language_masters = []

    for filepath in m4a_files:
        filename = os.path.basename(filepath)
        parts = filename.split(".")[0].split("_")  # audio_he.m4a → ['audio', 'he']
        if len(parts) < 2:
            continue
        lang_code = parts[1]

        # הפעלת המרה ל-HLS
        master_path, lang = convert_to_hls_versions(filepath, lang_code, output_folder)
        per_language_masters.append((master_path, lang))

        # העברת הקובץ שהסתיים לתיקיית done_m4a
        done_path = os.path.join(done_folder, filename)
        shutil.move(filepath, done_path)
        print(f"Moved {filename} to done_m4a/")

    generate_main_master(output_folder, per_language_masters, VIDEO_M3U8_PATH)
