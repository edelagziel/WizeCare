from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

model_name = "facebook/m2m100_418M"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

text = "Starting position: Sit with your back straight, hands supporting the back either behind or beside the body, elbows extended, legs straight and together in front of you. Move your right leg sideways with the knee extended. Wait for a second, then try to bring your left leg next to it. Wait another second, then return the left leg to the center, followed by the right."

tokenizer.src_lang = "en"
tgt_lang = "ru"

inputs = tokenizer(text, return_tensors="pt")
translated_tokens = model.generate(
    **inputs,
    forced_bos_token_id=tokenizer.get_lang_id(tgt_lang),
    max_length=1024,
    num_beams=5,
    no_repeat_ngram_size=2
)
translated_text = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)

# שמירה לקובץ בלבד (לא מדפיס למסך)
with open("translation.txt", "w", encoding="utf-8") as f:
    f.write(translated_text)
