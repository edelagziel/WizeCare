from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# טוען את המודל
model_name = "facebook/nllb-200-distilled-600M"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

# טקסט לתרגום
text = "Starting position: Sit with your back straight, hands supporting the back either behind or beside the body, elbows extended, legs straight and together in front of you. Move your right leg sideways with the knee extended. Wait for a second, then try to bring your left leg next to it. Wait another second, then return the left leg to the center, followed by the right."

# קביעת שפות
src_lang = "eng_Latn"
tgt_lang = "rus_Cyrl"
tokenizer.src_lang = src_lang

# קידוד ותרגום
inputs = tokenizer(text, return_tensors="pt")
translated_tokens = model.generate(**inputs, forced_bos_token_id=tokenizer.lang_code_to_id[tgt_lang])
translated_text = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)

# שמירה לקובץ
with open("translation.txt", "w", encoding="utf-8") as f:
    f.write(translated_text)
