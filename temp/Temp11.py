import re

# --- קובץ טיימקודים וטקסט באנגלית ---
with open("EngAudio.txt", encoding="utf-8") as f:
    eng_lines = f.readlines()

timestamps = []
items_per_line = []
for line in eng_lines:
    m = re.match(r"\[(\d+:\d+:\d+\.\d+) --> (\d+:\d+:\d+\.\d+)](.*)", line)
    if m:
        start, end, text = m.groups()
        timestamps.append((start, end))
        # ספירה של כמה מספרים מופיעים בשורה באנגלית (1,2,3 וכו')
        count = len(re.findall(r'\b\d[\.\s]?', text))
        if count == 0:
            count = 1
        items_per_line.append(count)

# --- הטקסט הערבי שלך כמו שהוא (בלוק אחד) ---
arabic_block = """
اثنان: أثناء القيام بهذا التمرين، حافظ على الوضع الصحيح من خلال إبقاء ظهرك مستقيمًا وعضلات بطنك مشغولة طوال الوقت. تأكد من أن ركبتيك تبقى مستقيمة.
الثالثة: خلال الحركة بأكملها، تأكد من أن ركبتيك تبقى مستقيمة لمنع تعريض تقنيتك للخطر.
أربعة
خمسة: تهانينا لقد أكملتم التمرين بنجاح
الآن، كرر نفس التمرين على الجانب الآخر.
واحد.
-ثانيه
ثلاثة
أربعة
خمسة: عمل ممتاز لقد أكملت التمرין بنجاح על كلا الجانبين
"""

# --- פיצול הטקסט הערבי האוטומטי לפי נקודות, ספירות ומילות מפתח ---
split_arabic = re.split(
    r'(?<=[\.!\?])\s+|'  # אחרי נקודה או סימן קריאה
    r'(?=(?:واحد|اثنان|ثانيه|ثلاثة|أربعة|خمسة|ستة|سبعة|ثمانية|تسعة|عشرة)[\:\.\s])', 
    arabic_block
)

arabic_lines = [x.strip('- .،:\n') for x in split_arabic if x and x.strip('- .،:\n')]

# --- חלוקה לערבית לפי מספר הפריטים בשורת האנגלית ---
arabic_pointer = 0
output_lines = []

for i, (start, end) in enumerate(timestamps):
    count = items_per_line[i]
    group = arabic_lines[arabic_pointer:arabic_pointer + count]
    arabic_pointer += count
    output_lines.append(f"[{start} --> {end}] {' '.join(group)}")

# --- כתיבה לקובץ סופי ---
with open("ArabicAudio_byNumbers.txt", "w", encoding="utf-8") as f:
    for line in output_lines:
        f.write(line + "\n")

print("נוצר הקובץ ArabicAudio_byNumbers.txt עם טיימקודים + טקסט בערבית מותאם.")
