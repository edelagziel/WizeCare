import whisperx  # This is the original WhisperX library for transcription
import shutil
from pathlib import Path
from pipeline_config import AUDIO_DIR, AUDIO_DONE_DIR, TEXT_DIR

def transcribe_latest_audio():
    # Define directories for audio input, text output, and processed audio.
    audio_dir = AUDIO_DIR
    text_dir = TEXT_DIR
    done_dir = AUDIO_DONE_DIR

    # Ensure all necessary directories exist
    for d in [audio_dir, text_dir, done_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # List all supported audio files in the audio directory
    files = [
        f.name for f in audio_dir.iterdir()
        if f.is_file() and f.suffix.lower() in {
            ".wav", ".mp3", ".m4a", ".ogg", ".flac", ".mp4",
            ".aac", ".wma", ".alac", ".opus"
        }
    ]
    if not files:
        print("No audio file found in the folder!")
        return {"error": "No audio file found in the folder!"}

    # Find the most recently modified audio file
    latest_file = max(files, key=lambda f: (audio_dir / f).stat().st_mtime)
    audio_path = audio_dir / latest_file
    print(f"Selected audio: {audio_path}")

    # Load the WhisperX model (large-v3, CPU, int8 for efficiency)
    print("Loading model...")
    model = whisperx.load_model("large-v3", device="cpu", compute_type="int8")

    # Load the selected audio file
    print("Loading audio file...")
    audio = whisperx.load_audio(str(audio_path))

    # Transcribe the audio, translating to English and auto-detecting the source language
    print("Transcribing (Translate to English, auto-detect source language)...")
    # If you want to transcribe in English only, use: result = model.transcribe(audio, language="en")
    result = model.transcribe(audio, task="translate")

    def format_time(seconds):
        """
        Format seconds as hh:mm:ss.sss for timestamping.
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02}:{minutes:02}:{secs:06.3f}"

    lines = []        # List to store timestamped lines for output
    clean_lines = []  # List to store only the transcribed text (no timestamps)

    # Process each segment in the transcription result
    for segment in result["segments"]:
        start = segment["start"]
        end = segment["end"]
        text = segment["text"].strip()
        # Format: [start --> end] text
        lines.append(f"[{format_time(start)} --> {format_time(end)}] {text}")
        clean_lines.append(text)

    # Prepare output file paths
    base_name = Path(latest_file).stem
    output_txt = text_dir / "EngAudio.txt"
    clean_output_txt = text_dir / f"{base_name}_clean.txt"

    # Write the timestamped transcription to file
    with output_txt.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Optionally, write the clean text (no timestamps) to a separate file
    # Uncomment the following lines if you want to save the clean text:
    # with open(clean_output_txt, "w", encoding="utf-8") as f:
    #     f.write(" ".join(clean_lines))

    # Move the processed audio file to the 'done' directory to avoid reprocessing
    destination = done_dir / latest_file
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite processed audio: {destination}")
    shutil.move(str(audio_path), str(destination))

    # Return the results, including file paths and the clean text
    return {
        "result": "success",
        "txt_file": output_txt,
        "clean_txt_file": clean_output_txt,
        "clean_text": " ".join(clean_lines)
    }

if __name__ == "__main__":
    print(transcribe_latest_audio())
