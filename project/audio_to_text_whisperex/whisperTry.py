import whisperx
import os

audio_path = "audiofile/audio.mp3"

# Check if file exists
if not os.path.exists(audio_path):
    print(f"File not found: {audio_path}")
    exit()

print("Loading model...")
model = whisperx.load_model("large-v3", device="cpu", compute_type="int8")

print("Loading audio...")
audio = whisperx.load_audio(audio_path)

print("Transcribing and translating to English...")
result = model.transcribe(audio, task="translate")  # Auto-detect language, translate to English

print("Formatting with timestamps...")

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:06.3f}"

lines = []
for segment in result["segments"]:
    start = format_time(segment["start"])
    end = format_time(segment["end"])
    text = segment["text"]
    lines.append(f"[{start} --> {end}] {text}")

output_path = "translated_to_english.txt"
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Translated transcription saved to {output_path}")
