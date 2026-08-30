import os
import re
import tempfile
import shutil
from dotenv import load_dotenv
from pydub import AudioSegment
import azure.cognitiveservices.speech as speechsdk

# --- Azure Configuration: Load environment variables and set up Azure Speech Service ---
load_dotenv()
SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY_1")
REGION = os.getenv("AZURE_SPEECH_REGION")
if not SPEECH_KEY or not REGION:
    raise RuntimeError("Missing AZURE_SPEECH_KEY_1 or AZURE_SPEECH_REGION in .env file")

# Configure Azure Speech SDK with subscription key and region
speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=REGION)
speech_config.set_speech_synthesis_output_format(
    speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
)

# Mapping from language code to Azure voice name
VOICE_BY_LANG = {
    "ru": "ru-RU-DmitryNeural",          # Russian
    "es": "es-ES-ElviraNeural",          # Spanish
    "ar": "ar-EG-SalmaNeural",           # Arabic
    "pt": "pt-BR-ThalitaNeural",         # Portuguese
    "he": "he-IL-AvriNeural",            # Hebrew
    "en": "en-US-AvaMultilingualNeural", # English
    "default": "en-US-AvaMultilingualNeural", # Default voice
}

# Mapping from language code to XML language code for SSML
XML_LANG_BY_LANG = {
    "ru": "ru-RU",
    "es": "es-ES",
    "ar": "ar-EG",
    "pt": "pt-BR",
    "he": "he-IL",
    "en": "en-US",
    "default": "en-US",
}

# Characters per second for each language, used to estimate speech rate
CHARS_PER_SEC = {
    "ru": 15,      # Russian
    "pt": 12,      # Portuguese
    "ar": 14,      # Arabic
    "es": 15,      # Spanish
    "default": 13  # Default if language not specified
}

# Regular expression to parse timestamped lines in the format: [hh:mm:ss.ms --> hh:mm:ss.ms] text
TS_RE = re.compile(r"\[(?P<start>[\d:.]+)\s*-->\s*(?P<end>[\d:.]+)\]\s*(?P<text>.*)")

def parse_time_ms(s: str) -> int:
    """
    Parse a timestamp string in the format hh:mm:ss.ms into milliseconds.
    """
    hh, mm, rest = s.split(":")
    ss, ms = rest.split(".")
    total_ms = (int(hh) * 3600 + int(mm) * 60 + int(ss)) * 1000 + int(ms)
    print(f"Parsed time: {hh}:{mm}:{ss}.{ms} → {total_ms} ms")
    return total_ms

def read_items(path: str):
    """
    Read timestamped text items from a file and return a list of dictionaries with start, end, and text.
    Each line should be in the format: [hh:mm:ss.ms --> hh:mm:ss.ms] text
    """
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for i, ln in enumerate(f, start=1):
            ln = ln.strip()
            if not ln:
                print(f"Line {i} is empty, skipping")
                continue

            m = TS_RE.match(ln)
            if not m:
                print(f"Line {i} does not match expected format: {ln}")
                continue

            start = parse_time_ms(m.group("start"))
            end = parse_time_ms(m.group("end"))
            txt = m.group("text").strip()

            obj = {"start": start, "end": end, "text": txt}
            print(f"Line {i} -> {obj}")

            items.append(obj)

    print("\nAll parsed items:")
    print(items)
    return items

def build_ssml(text: str, xml_lang: str, voice_name: str, rate_val: float) -> str:
    """
    Build an SSML string for Azure TTS with a custom speaking rate.
    The rate_val is mapped to SSML rate keywords.
    """
    # Map the numeric rate value to an SSML rate string (clamped between 0.5 and 1.6)
    if rate_val > 1.6:
        rate_str = "x-fast"
    elif rate_val > 1.4:
        rate_str = "fast"
    elif rate_val > 0.55:
        rate_str = "medium"
    elif rate_val > 0.4:
        rate_str = "slow"
    else:
        rate_str = "x-slow"
    print(f"SSML: chars={len(text)}, rate={rate_val:.2f}, rate_ssml={rate_str}")
    return f"""<speak version="1.0" xml:lang="{xml_lang}">
  <voice name="{voice_name}">
    <prosody rate="{rate_str}">
      {text}
    </prosody>
  </voice>
</speak>"""

def synthesize_ssml(text: str, out_path: str, voice: str, xml_lang: str, seg_duration: int, lang_code: str):
    """
    Synthesize speech from SSML and save to a WAV file.
    If the text is empty, generate silence for the segment duration.
    The speech rate is estimated based on language and segment duration.
    """
    if not text.strip():
        # If the text is empty, export silence for the segment duration
        silent = AudioSegment.silent(duration=seg_duration)
        silent.export(out_path, format="wav")
        return

    # Get the characters per second for the language, or use default
    chars_per_sec = CHARS_PER_SEC.get(lang_code, CHARS_PER_SEC["default"])

    # Estimate how long the text would take to read at normal speed (in ms)
    est_normal_ms = len(text) / chars_per_sec * 1000
    rate_val = est_normal_ms / seg_duration

    # Clamp rate_val to the range used in build_ssml (0.5..1.6)
    rate_val = min(max(rate_val, 0.5), 1.6)

    # Build SSML and synthesize speech
    ssml = build_ssml(text, xml_lang, voice, rate_val)
    audio_cfg = speechsdk.audio.AudioOutputConfig(filename=out_path)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_cfg)
    result = synthesizer.speak_ssml_async(ssml).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        # If synthesis fails, export silence for the segment
        cancel = result.cancellation_details
        print(f"WARNING: TTS failed for '{text[:30]}'... Skipping segment. Reason: {cancel.reason} {getattr(cancel, 'error_details','')}")
        silent = AudioSegment.silent(duration=seg_duration)
        silent.export(out_path, format="wav")

def render_by_timestamps(timed_path: str, out_wav: str, lang_code: str):
    """
    Render a full audio file by synthesizing each timestamped segment and concatenating them.
    The output audio will match the timing of the input timestamped text file.
    """
    items = read_items(timed_path)
    if not items:
        raise ValueError("No items parsed from the timestamped file.")

    # Select the appropriate voice and xml_lang for the language
    voice = VOICE_BY_LANG.get(lang_code, VOICE_BY_LANG["default"])
    xml_lang = XML_LANG_BY_LANG.get(lang_code, XML_LANG_BY_LANG["default"])

    # Create a temporary directory for storing segment files
    tmpdir = tempfile.mkdtemp(prefix="tts_segments_")
    try:
        # Start with silence up to the first segment's start time
        timeline = AudioSegment.silent(duration=items[0]["start"])
        for i, item in enumerate(items):
            seg_path = os.path.join(tmpdir, f"seg_{i}.wav")
            seg_duration = item["end"] - item["start"]

            # Synthesize the segment for the current text and timing
            synthesize_ssml(item["text"], seg_path, voice, xml_lang, seg_duration, lang_code)

            # Load the synthesized segment and append it to the timeline
            seg = AudioSegment.from_wav(seg_path)
            timeline += seg

            # If there is a gap to the next segment, add silence to fill the gap
            curr_end = item["end"]
            curr_len = len(timeline)
            if curr_end > curr_len:
                timeline += AudioSegment.silent(duration=curr_end - curr_len)

        # Ensure the output directory exists and export the final audio file
        os.makedirs(os.path.dirname(out_wav) or ".", exist_ok=True)
        timeline.export(out_wav, format="wav")
        print(f"OK: voice={voice} saved_to={out_wav} (duration: {len(timeline)/1000:.2f} sec)")
        # Warn if the final audio is much longer or shorter than expected
        if abs(len(timeline) - items[-1]["end"]) > 1500:
            print(f" WARNING: final audio longer/shorter than expected by {abs(len(timeline) - items[-1]['end'])/1000:.2f} sec")
    finally:
        # Clean up temporary files and directory
        shutil.rmtree(tmpdir, ignore_errors=True)

# --- Example Run ---
if __name__ == "__main__":
    # Example usage: render Hebrew audio from TimedText.txt
    lang_code = "he"  # Set the language code you want to use
    TIMED_TXT = r"TimedText.txt"
    OUTPUT = fr"done_all/output_{lang_code}_clean.wav"
    render_by_timestamps(TIMED_TXT, OUTPUT, lang_code=lang_code)
