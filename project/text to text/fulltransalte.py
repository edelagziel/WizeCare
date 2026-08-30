from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
import requests
import json

# --- הגדרות מודל תרגום (NLLB/M2M100) ---
model_name = "facebook/nllb-200-1.3B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

# --- קריאת קלט מהקובץ ---
input_filename = input("Enter input file name (e.g. input.txt): ").strip()
with open(input_filename, "r", encoding="utf-8") as f:
    text = f.read().strip()

# --- זיהוי שפה ---
lang_id = pipeline("text-classification", model="papluca/xlm-roberta-base-language-detection")
detected = lang_id(text[:200])[0]["label"].lower()
print(f"Detected language: {detected}")

# --- מיפוי שפה (שינוי לפי הצורך) ---
lang_map = {
    "he": "heb_Latn",
    "ar": "ara_Arab",
    "en": "eng_Latn",
    "ru": "rus_Cyrl",
    "es": "spa_Latn",
    "pt": "por_Latn"
}

src_lang = lang_map.get(detected, "eng_Latn")

# --- בחירת שפת יעד ---
tgt_input = input("Enter target language (en / ar / ru / es / he / pt): ").strip().lower()
tgt_lang = lang_map.get(tgt_input, "eng_Latn")

# --- תרגום (אם צריך) ---
if detected != tgt_input:
    tokenizer.src_lang = src_lang
    inputs = tokenizer(text, return_tensors="pt")
    translated_tokens = model.generate(
        **inputs,
        forced_bos_token_id=tokenizer.lang_code_to_id[tgt_lang],
        max_length=1024,
        num_beams=5,
        no_repeat_ngram_size=2
    )
    translation = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
else:
    translation = text  # אם המקור כבר בשפת היעד

print("\n--- Raw Translation / Input to LLM ---\n")
print(translation)

# --- בניית הפרומפט לפי השפה ---
prompts = {
    "en": "Rewrite the following as clear, professional English physical therapy instructions for a patient. Make the text natural, easy to follow, and medically accurate, but do not add or remove any steps or details. Keep the structure and order of sentences as in the original.\n\n",
    "ru": "Прочитай этот текст и перепиши его по-русски так, чтобы он был максимально понятен, естественен и медицински корректен для пациента, но не добавляй никакой дополнительной информации, не расширяй и не сокращай смысл. Сохрани структуру, длину и порядок фраз как в оригинале. Просто сделай текст плавным, но максимально близким к оригиналу.\n\n",
    "es": "Reescribe el siguiente texto como instrucciones de fisioterapia en español claras, profesionales y fáciles de seguir para un paciente. No añadas ni quites pasos o detalles. Mantén la estructura y el orden de las frases como en el original.\n\n",
    "ar": "أعد كتابة النص التالي كتعليمات علاج طبيعي باللغة العربية تكون واضحة ومهنية وسهلة المتابعة للمريض، دون إضافة أو حذف أي خطوات أو تفاصيل. حافظ على البنية وترتيب الجمل كما في الأصل.\n\n",
    "he": "שכתב את ההוראות בצורה ברורה, מקצועית, טבעית וללא תוספות או קיצורים. שמור על המבנה והסדר של המשפטים בדיוק כמו במקור.\n\n"
}

# קבל פרומפט לפי יעד, אם אין — ברירת מחדל אנגלית
prompt = prompts.get(tgt_input, prompts["en"]) + translation

# --- שליחת בקשה ל־Ollama LLM (דרך API מקומי) ---
# ודא ש-Ollama רץ במחשב שלך עם llama3:instruct
payload = {
    "model": "llama3:instruct",
    "prompt": prompt,
    "stream": False
}

response = requests.post("http://localhost:11434/api/generate", json=payload)
output = response.json()['response']

# --- שמירת הפלט לקובץ ---
with open("llm_output.txt", "w", encoding="utf-8") as f:
    f.write(output)

print("\n--- Improved Output by LLM ---\n")
print(output)
