import os
import glob
import shutil
from pydub import AudioSegment

def convert_and_move_wav(folder_wav, folder_m4a, folder_done, bitrate="192k"):
    # חפש קובצי WAV בתיקייה
    wav_files = glob.glob(os.path.join(folder_wav, "*.wav"))
    if not wav_files:
        print("No WAV files found in", folder_wav)
        return

    # קובץ ה-WAV הכי עדכני
    latest_wav = max(wav_files, key=os.path.getmtime)
    print("Selected WAV:", latest_wav)

    # יצירת תיקיות ליעד אם לא קיימות
    os.makedirs(folder_m4a, exist_ok=True)
    os.makedirs(folder_done, exist_ok=True)

    # המרה ל-m4a ושמירה בתיקיית mp4a
    base_name = os.path.splitext(os.path.basename(latest_wav))[0]
    output_m4a_path = os.path.join(folder_m4a, base_name + ".m4a")

    audio = AudioSegment.from_wav(latest_wav)
    audio.export(output_m4a_path, format="ipod", bitrate=bitrate)
    print(" Converted and saved as:", output_m4a_path)

    # העברת קובץ ה־WAV לתיקיית wavdone
    destination_wav_path = os.path.join(folder_done, os.path.basename(latest_wav))
    shutil.move(latest_wav, destination_wav_path)
    print(" Moved original WAV to:", destination_wav_path)

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))

    folder_wav   = os.path.join(base_dir, "WAV")
    folder_m4a   = os.path.join(base_dir, "mp4a")
    folder_done  = os.path.join(base_dir, "wavdone")

    convert_and_move_wav(folder_wav, folder_m4a, folder_done)
