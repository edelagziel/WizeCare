import whisperx
import os
import shutil

def transcribe_latest_audio():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(base_dir, "audiofile")
    text_dir = os.path.join(base_dir, "TextFiles")
    done_dir = os.path.join(base_dir, "audioDone")


    # Ensure all directories exist
    for d in [audio_dir, text_dir, done_dir]:
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

    # 1. Find the most recent audio file
    files = [f for f in os.listdir(audio_dir) if f.lower().endswith((".wav", ".mp3", ".m4a", ".ogg", ".flac", ".mp4", ".aac", ".wma", ".alac", ".opus"))]
    if not files:
        print("No audio file found in the folder!")
        return {"error": "No audio file found in the folder!"}

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(audio_dir, f)))
    audio_path = os.path.join(audio_dir, latest_file)
    print(f"Selected audio: {audio_path}")

    # 2. Load the model
    print("Loading model...")
    model = whisperx.load_model("large-v3", device="cpu", compute_type="int8")

    print("Loading audio file...")
    audio = whisperx.load_audio(audio_path)

    print("Transcribing (English only)...")
    result = model.transcribe(audio, language="en")  # Force English transcription

    # 3. Format with timestamps
    def format_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02}:{minutes:02}:{secs:06.3f}"

    lines = []
    for segment in result["segments"]:
        start = segment["start"]
        end = segment["end"]
        text = segment["text"]
        lines.append(f"[{format_time(start)} --> {format_time(end)}] {text}")

    # 4. Save to text folder
    base_name = os.path.splitext(latest_file)[0]
    output_txt = os.path.join(text_dir, f"{base_name}.txt")
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Transcription saved to: {output_txt}")

    # 5. Move the audio to audioDone
    shutil.move(audio_path, os.path.join(done_dir, latest_file))
    print(f"Audio moved to: {done_dir}")

    # Success
    return {"result": "success", "txt_file": output_txt}

if __name__ == "__main__":
    print(transcribe_latest_audio())
