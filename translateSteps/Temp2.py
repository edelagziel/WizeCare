from ollama import Client

# התחברות ל־Ollama המקומי
client = Client(host='http://localhost:11434')  # ברירת המחדל

def run_llama_cleaning(original_text: str) -> str:
    """מבצע ניקוי טקסט רפואי באמצעות שני פרומפטים ומחזיר טקסט סופי ברור ונקי"""

    # פרומט 1 – המרת מספרים למילים
    prompt_1 = f"""
    You must replace every standalone digit (e.g. 1, 2, 3...) in the following text with its full English word (e.g. one, two, three).
    Rules:
    - Only digits that appear as separate words (not part of times, units, or decimals).
    - Do not modify punctuation or other words.
    - Do not add explanation, examples, or headings.
    - Output ONLY the updated text, nothing else.
    - Do not number or format the sentences. Just replace digits with their word equivalents.

    Text:
    \"\"\"{original_text}\"\"\"
    """


    output_1 = run_prompt_llama(prompt_1)

    # פרומט 2 – שכתוב ברור רפואי
    prompt_2 = f"""
        Rewrite the following physical therapy instructions as clear and complete English sentences.
        Use correct grammar and a calm, professional tone.
        Do not change the order or meaning of the actions.
        Keep the sentences short and simple to ensure accurate translation into other languages.
        Avoid adding extra explanation or medical terminology.

    Text:
    \"\"\"{output_1}\"\"\"
    """

    output_2 = run_prompt_llama(prompt_2)
    return output_2.strip()


def run_prompt_llama(prompt: str) -> str:
    """מריץ שיחה מול מודל LLaMA ומחזיר את הפלט כטקסט נקי בלבד"""
    try:
        response = client.chat(model='llama3:instruct', messages=[
            {"role": "user", "content": prompt}
        ])
        return response['message']['content'].strip()
    except Exception as e:
        print(f" Error running prompt: {e}")
        return ""
