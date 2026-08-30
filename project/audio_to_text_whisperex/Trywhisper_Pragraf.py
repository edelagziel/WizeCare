import whisperx
import os

audio_path = "audiofile/audio.wav"

# Check if file exists
if not os.path.exists(audio_path):
    print(f"File not found: {audio_path}")
    exit()

print("Loading model...")
model = whisperx.load_model("large-v3", device="cpu", compute_type="int8")

print("Loading audio...")
audio = whisperx.load_audio(audio_path)

print("Transcribing...")
result = model.transcribe(audio)

print("Formatting with timestamps...")

# Format output with timecodes
lines = []
for segment in result["segments"]:
    start = segment["start"]
    end = segment["end"]
    text = segment["text"]

    def format_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02}:{minutes:02}:{secs:06.3f}"

    start_time = format_time(start)
    end_time = format_time(end)
    lines.append(f"[{start_time} --> {end_time}] {text}")

# Save to file
output_path = "transcribed_times.txt"
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Transcription saved to {output_path}")
