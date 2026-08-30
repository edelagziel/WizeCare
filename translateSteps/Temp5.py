import os
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

# -------- Config --------
load_dotenv()
SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY_1")
REGION     = os.getenv("AZURE_SPEECH_REGION")

if not SPEECH_KEY or not REGION:
    raise RuntimeError("Missing AZURE_SPEECH_KEY_1 or AZURE_SPEECH_REGION in .env")

speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=REGION)
speech_config.set_speech_synthesis_output_format(
    speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
)

VOICE_BY_LANG = {
    "ru": "ru-RU-DmitryNeural",
    "es": "es-ES-ElviraNeural",
    "ar": "ar-EG-SalmaNeural",
    "pt": "pt-BR-ThalitaNeural",
    "he": "he-IL-AvriNeural",  # דוגמה לעברית, אם תרצה להוסיף
    "en": "en-US-AvaMultilingualNeural",
    "default": "en-US-AvaMultilingualNeural",
}

def build_ssml(text: str, lang_code: str, voice_name: str, slow: bool = True) -> str:
    rate = "slow" if slow else "medium"
    return f"""<speak version="1.0" xml:lang="{lang_code}">
  <voice name="{voice_name}">
    <prosody rate="{rate}">
      {text}
    </prosody>
  </voice>
</speak>"""

def tts(text: str, lang: str, to_file: str | None = None, use_ssml: bool = True, slow: bool = True):
    voice = VOICE_BY_LANG.get(lang, VOICE_BY_LANG["default"])
    if to_file:
        audio_cfg = speechsdk.audio.AudioOutputConfig(filename=to_file)
    else:
        audio_cfg = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_cfg)

    if use_ssml:
        xml_lang = {
            "ru": "ru-RU",
            "es": "es-ES",
            "ar": "ar-EG",
            "pt": "pt-BR",
            "he": "he-IL",
            "en": "en-US",
        }.get(lang, "en-US")
        ssml = build_ssml(text, xml_lang, voice, slow=slow)
        result = synthesizer.speak_ssml_async(ssml).get()
    else:
        speech_config.speech_synthesis_voice_name = voice
        result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"OK: voice={voice} saved_to={to_file or 'speaker'}")
    else:
        cancel = result.cancellation_details
        print("FAILED:", cancel.reason, getattr(cancel, "error_details", ""))
