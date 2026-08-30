import os
import shutil
import time
import whisperx
import torch

def transcribe_latest_audio(target_lang="auto", batch_size=16):
    """
    target_lang: "he" | "en" | "auto"
    אם 'auto' – WhisperX יזהה, אך זה איטי יותר. עדיף לקבע he/en כשאפשר.
    """
    base_dir  = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(base_dir, "audiofile")
    text_dir  = os.path.join(base_dir, "TextFiles")
    done_dir  = os.path.join(base_dir, "audioDone")

    for d in (audio_dir, text_dir, done_dir):
        os.makedirs(d, exist_ok=True)

    exts  = (".wav",".mp3",".m4a",".ogg",".flac",".mp4",".aac",".wma",".alac",".opus")
    files = [f for f in os.listdir(audio_dir) if f.lower().endswith(exts)]
    if not files:
        msg = "No audio file found in the folder!"
        print(msg); return {"error": msg}

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(audio_dir, f)))
    audio_path  = os.path.join(audio_dir, latest_file)
    print(f"Selected audio: {audio_path}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    print(f"Loading model... (device={device}, compute_type={compute_type})")
    t0 = time.perf_counter()
    model = whisperx.load_model("large-v3", device=device, compute_type=compute_type)

    print("Loading audio file...")
    audio = whisperx.load_audio(audio_path)

    print(f"Transcribing (language='{target_lang}', batch_size={batch_size})...")
    t1 = time.perf_counter()
    if target_lang in ("he","en"):
        result = model.transcribe(audio, language=target_lang, batch_size=batch_size)
    else:
        # auto – עשוי להפעיל VAD/זיהוי שפה → איטי יותר
        result = model.transcribe(audio, batch_size=batch_size)
    t2 = time.perf_counter()

    def ftime(sec: float) -> str:
        hh = int(sec // 3600); mm = int((sec % 3600) // 60); ss = sec % 60
        return f"{hh:02}:{mm:02}:{ss:06.3f}"

    segments = result.get("segments", []) or []
    lines = []
    for seg in segments:
        start = seg.get("start", 0.0); end = seg.get("end", 0.0); text = seg.get("text", "").strip()
        lines.append(f"[{ftime(start)} --> {ftime(end)}] {text}")

    base_name  = os.path.splitext(latest_file)[0]
    output_txt = os.path.join(text_dir, f"{base_name}.txt")

    try:
        with open(output_txt, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Transcription saved to: {output_txt}")
        print(f"Timings: model_load={t1-t0:.1f}s, transcribe={t2-t1:.1f}s, total={time.perf_counter()-t0:.1f}s")
        return {"result": "success", "txt_file": output_txt}
    finally:
        try:
            shutil.move(audio_path, os.path.join(done_dir, latest_file))
            print(f"Audio moved to: {done_dir}")
        except Exception as e:
            print(f"Warning: could not move audio to done folder: {e}")

if __name__ == "__main__":
    print(transcribe_latest_audio(target_lang="auto", batch_size=16))
