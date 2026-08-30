from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import re

# טוען את המודל
model_name = "facebook/nllb-200-1.3B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

# קלט מהקובץ
input_filename = input("Enter input file name (e.g. input.txt): ").strip()
with open(input_filename, "r", encoding="utf-8") as f:
    text = f.read().strip()

# הגדרת שפות
src_lang = "eng_Latn"
tgt_lang = "rus_Cyrl"  # שנה לפי הצורך
tokenizer.src_lang = src_lang

# פיצול ידני למשפטים לפי נקודות, סימני קריאה ושאלה
sentences = re.split(r'(?<=[.!?])\s+', text)
translated_sentences = []

# תרגום כל משפט בנפרד
for sentence in sentences:
    if sentence.strip() == "":
        continue
    inputs = tokenizer(sentence, return_tensors="pt")
    translated_tokens = model.generate(
        **inputs,
        forced_bos_token_id=tokenizer.lang_code_to_id[tgt_lang],
        max_length=512,
        num_beams=5,
        no_repeat_ngram_size=2
    )
    translated = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
    translated_sentences.append(translated)

# איחוד ושמירה
full_translation = " ".join(translated_sentences)
with open("translation.txt", "w", encoding="utf-8") as f:
    f.write(full_translation)

print(" Translation complete.")


# this code got rated 6.5