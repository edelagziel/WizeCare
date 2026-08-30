import os, re, tempfile, shutil
from dotenv import load_dotenv
from pydub import AudioSegment
import azure.cognitiveservices.speech as speechsdk

# ---------- Azure config ----------
load_dotenv()
SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY_1")
REGION     = os.getenv("AZURE_SPEECH_REGION")
if not SPEECH_KEY or not REGION:
    raise RuntimeError("Missing AZURE_SPEECH_KEY_1 or AZURE_SPEECH_REGION in .env")

speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=REGION)
speech_config.set_speech_synthesis_output_format(
    speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
)

VOICE = "ar-EG-SalmaNeural"
XML_LANG = "ar-EG"

# ---------- Timed file parsing ----------
TS_RE = re.compile(r"\[(?P<start>[\d:.]+)\s*-->\s*(?P<end>[\d:.]+)\]\s*(?P<text>.+)")

def parse_time_ms(s: str) -> int:
    hh, mm, rest = s.split(":")
    ss, ms = rest.split(".")
    return (int(hh)*3600 + int(mm)*60 + int(ss))*1000 + int(ms)

def read_items(path: str):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln: continue
            m = TS_RE.match(ln)
            if not m: continue
            start = parse_time_ms(m.group("start"))
            end   = parse_time_ms(m.group("end"))
            txt   = m.group("text").strip()
            items.append({"start": start, "end": end, "text": txt})
    return items

# ---------- SSML ----------
def build_ssml_arabic(text: str, rate="medium") -> str:
    return f"""
<speak version="1.0" xml:lang="{XML_LANG}">
  <voice name="{VOICE}">
    <prosody rate="{rate}">
      {text}
    </prosody>
  </voice>
</speak>
"""

def synthesize_ssml(text: str, out_path: str, rate="-20%"):
    ssml = build_ssml_arabic(text, rate)
    audio_cfg = speechsdk.audio.AudioOutputConfig(filename=out_path)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_cfg)
    result = synthesizer.speak_ssml_async(ssml).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        cancel = result.cancellation_details
        raise RuntimeError(f"TTS failed: {cancel.reason} {getattr(cancel, 'error_details','')}")

# ---------- Render ----------
def render_by_timestamps(timed_path: str, out_wav: str):
    items = read_items(timed_path)
    if not items:
        raise ValueError("No items parsed.")

    tmpdir = tempfile.mkdtemp(prefix="tts_segments_")
    try:
        timeline = AudioSegment.silent(duration=items[0]["start"])
        for i, item in enumerate(items):
            seg_path = os.path.join(tmpdir, f"seg_{i}.wav")
            synthesize_ssml(item["text"], seg_path, rate="-20%")
            seg = AudioSegment.from_wav(seg_path)
            timeline += seg

            next_start = items[i+1]["start"] if i+1 < len(items) else items[-1]["end"]
            gap = max(0, next_start - len(timeline))
            timeline += AudioSegment.silent(duration=gap)

        os.makedirs(os.path.dirname(out_wav) or ".", exist_ok=True)
        timeline.export(out_wav, format="wav")
        print(f" Done: {out_wav} (duration: {len(timeline)/1000:.2f} sec)")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

# ---------- Run ----------
if __name__ == "__main__":
    TIMED_TXT = r"ArabicAudio_byNumbers.txt"
    OUTPUT    = r"done_all/Arabic_byNumbers_clean.wav"
    render_by_timestamps(TIMED_TXT, OUTPUT)
