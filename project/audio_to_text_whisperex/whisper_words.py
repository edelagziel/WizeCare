import whisperx

# Load model
model = whisperx.load_model("large-v3", device="cpu", compute_type="int8")

# Load audio
audio_path = "./audiofile/audio.mp3"
audio = whisperx.load_audio(audio_path)

# Transcribe
result = model.transcribe(audio, language="en")

# Load alignment model (בגרסה שלך אין צורך לשלוט בשם המודל)
align_model, metadata = whisperx.load_align_model(language_code="en", device="cpu")

# Align (גרסה ישנה – בלי align_model)
aligned_result = whisperx.align(
    result["segments"],
    align_model,
    metadata,
    audio,
    device="cpu"
)

# Extract word-level segments
word_segments = aligned_result["word_segments"]

# Save to file
with open("word_timestamps.txt", "w", encoding="utf-8") as f:
    for word in word_segments:
        f.write(f"[{word['start']:.2f} --> {word['end']:.2f}] {word.get('text', word.get('word', ''))}\n")

