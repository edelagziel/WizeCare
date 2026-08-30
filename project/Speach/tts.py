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
# קידוד אודיו טוב כברירת מחדל; אפשר לשנות לפי צורך
speech_config.set_speech_synthesis_output_format(
    speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
)

# -------- Voice map by language --------
VOICE_BY_LANG = {
    # exact voices you asked
    "ru": "ru-RU-DmitryNeural",     # Russian
    "es": "es-ES-ElviraNeural",     # Spanish (Spain). For LatAm consider es-MX-DaliaNeural
    "ar": "ar-EG-SalmaNeural",      # Arabic (Egypt)
    "pt": "pt-BR-ThalitaNeural",    # Portuguese (Brazil)
    # fallback
    "default": "en-US-AvaMultilingualNeural",
}

def build_ssml(text: str, lang_code: str, voice_name: str, slow: bool = True) -> str:
    """
    מייצר SSML עדין (איטי) שמותאם לטקסטי פיזיותרפיה.
    אם לא רוצים SSML – אפשר פשוט להשתמש ב-speak_text_async.
    """
    rate = "slow" if slow else "medium"
    return f"""<speak version="1.0" xml:lang="{lang_code}">
  <voice name="{voice_name}">
    <prosody rate="{rate}">
      {text}
    </prosody>
  </voice>
</speak>"""

def tts(text: str, lang: str, to_file: str | None = None, use_ssml: bool = True, slow: bool = True):
    """
    text  – הטקסט להקראה
    lang  – 'ru'/'es'/'ar'/'pt' (או אחר – ייפול ל-fallback)
    to_file – אם None ינוגן ברמקול; אם נתיב – יישמר קובץ WAV
    use_ssml – להשתמש ב-SSML (מומלץ לטקסטים טיפוליים)
    slow – לקרוא לאט יותר (SSML בלבד)
    """
    voice = VOICE_BY_LANG.get(lang, VOICE_BY_LANG["default"])

    if to_file:
        audio_cfg = speechsdk.audio.AudioOutputConfig(filename=to_file)
    else:
        audio_cfg = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_cfg)

    if use_ssml:
        # קובע גם xml:lang נכון (חשוב לערבית ועברית)
        # מיפוי xml:lang בסיסי:
        xml_lang = {
            "ru": "ru-RU",
            "es": "es-ES",
            "ar": "ar-EG",
            "pt": "pt-BR",
        }.get(lang, "en-US")

        ssml = build_ssml(text, xml_lang, voice, slow=slow)
        result = synthesizer.speak_ssml_async(ssml).get()
    else:
        # ללא SSML – פשוט מגדירים את הקול ומקריאים
        synthesizer.properties = synthesizer.properties
        speech_config.speech_synthesis_voice_name = voice
        result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"OK: voice={voice} saved_to={to_file or 'speaker'}")
    else:
        cancel = result.cancellation_details
        print("FAILED:", cancel.reason, getattr(cancel, "error_details", ""))


if __name__ == "__main__":
    txt_ru = "Сядьте прямо. Положите руки рядом с телом. Теперь медленно вытяните правую ногу в сторону."
    txt_es = "Siéntese derecho. Coloque las manos a los lados del cuerpo. Ahora extienda lentamente la pierna derecha."
    txt_ar = "اجلس بشكل مستقيم. ضع يديك بجانب جسمك. الآن مدّ ساقك اليمنى ببطء إلى الجانب."
    txt_pt = "Sente-se ereto. Coloque as mãos ao lado do corpo. Agora estenda lentamente a perna direita."

    # דוגמאות – ניגון לרמקולים:
    tts(txt_ru, "ru", to_file=None, use_ssml=True, slow=True)
    tts(txt_es, "es", to_file=None, use_ssml=True, slow=True)
    tts(txt_ar, "ar", to_file=None, use_ssml=True, slow=True)
    tts(txt_pt, "pt", to_file=None, use_ssml=True, slow=True)

    # ואם רוצים קובץ WAV:
    # tts(txt_es, "es", to_file="es_demo.wav", use_ssml=True, slow=True)
