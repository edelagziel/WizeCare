from ollama import Client

# Connect to the local Ollama server
client = Client(host='http://localhost:11434')


def review_arabic_translation(english_text: str, arabic_translation: str) -> str:
    """
    Requests the LLM to review the Arabic translation of English physical therapy instructions,
    provide comments, and rate the translation quality.
    Returns the review as a string (in English).
    """
    # Construct the prompt for the LLM to review the translation
    prompt = f"""
You are an Arabic language reviewer.

Your task:
- Review the following Arabic translation of English physical therapy instructions.
- Comment on the quality of the translation in terms of clarity, grammar, natural flow, and fidelity to the original English.
- Identify any mistakes, unnatural phrasing, or missing elements.
- Warn about any misuse of medical terms such as "كفاءة الركبة".
- Give a score from 1 to 10 at the end.
- Respond only in English.

---

English Source:
\"\"\"{english_text.strip()}\"\"\"


Arabic Translation:
\"\"\"{arabic_translation.strip()}\"\"\"


Now write your review and give a score from 1 to 10 at the end.
    """

    try:
        # Send the prompt to the LLM and get the response
        response = client.chat(model='llama3:instruct', messages=[
            {"role": "user", "content": prompt}
        ])
        # Return the review content (stripped of leading/trailing whitespace)
        return response['message']['content'].strip()
    except Exception as e:
        # Print error and return error message if something goes wrong
        print("Error reviewing translation:", e)
        return "[ERROR] Failed to review translation."


def improve_translation_based_on_review(english_text: str, arabic_translation: str, review_notes: str) -> str:
    """
    Uses the review notes provided by the LLM to improve the Arabic translation.
    Returns the improved Arabic translation as a string.
    """
    # Construct the prompt for the LLM to improve the translation based on its own review
    prompt = f"""
You previously reviewed the Arabic translation of English physical therapy instructions and gave the following feedback:

Review:
\"\"\"{review_notes.strip()}\"\"\"


Now improve the Arabic translation based on your own feedback above.
Instructions:
- Do not change the meaning or order of the English source.
- Do not include any introductory sentences such as "Here are the instructions..." in Arabic.
- Use common and medically accurate Arabic phrases only.
- Avoid incorrect terms such as "كفاءة الركبة".
- Preserve a clear, calm, and professional tone in Arabic.
- Respond with the full improved Arabic version only.

---

English Source:
\"\"\"{english_text.strip()}\"\"\"


Original Arabic Translation:
\"\"\"{arabic_translation.strip()}\"\"\"    
    """

    try:
        # Send the prompt to the LLM and get the improved translation
        response = client.chat(model='llama3:instruct', messages=[
            {"role": "user", "content": prompt}
        ])
        # Return the improved translation (stripped of leading/trailing whitespace)
        return response['message']['content'].strip()
    except Exception as e:
        # Print error and return error message if something goes wrong
        print("Error improving based on review:", e)
        return "[ERROR] Failed to improve translation."
