from ollama import Client

# Create a client to connect to the local Ollama server
client = Client(host='http://localhost:11434')  # Default host

def run_prompt_llama(prompt: str) -> str:
    """
    Sends a prompt to the Llama3 model via Ollama and returns the response as a string.
    """
    try:
        response = client.chat(model='llama3:instruct', messages=[
            {"role": "user", "content": prompt}
        ])
        return response['message']['content'].strip()
    except Exception as e:
        print(f"Error running prompt: {e}")
        return ""

def run_llama_cleaning(original_text: str) -> str:
    """
    Cleans and rewrites physical therapy instructions using Llama3 in two steps:
    1. Replaces every standalone digit with its full English word.
    2. Rewrites the instructions for clarity and professionalism, preserving all numbers and their order.
    Returns the cleaned and rewritten text.
    """

    # Step 1: Replace every standalone digit with its full English word
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

    # Step 2: Rewrite the instructions for clarity and professionalism, preserving all numbers and their order
    prompt_2 = f"""
Rewrite the following physical therapy instructions using correct grammar and a clear, professional tone.
- DO NOT remove, merge, or reorder any number, counting sequence, or repeated instructions (such as "one two three four five", "1 2 3 4 5", or any numbers).
- KEEP every number or counting sequence exactly as in the original.
- If a number appears as a digit or a word, keep it as a word (e.g., "three").
- Do not merge numbered steps into one sentence.
- Output only the translated instructions, with no headings or extra explanations.

Text:
\"\"\"{output_1}\"\"\"
"""
    output_2 = run_prompt_llama(prompt_2)
    return output_2.strip()

if __name__ == "__main__":
    # Example usage: test the cleaning pipeline with a sample text
    test_text = "2. Be sure to keep your back straight and stomach tight throughout the whole exercise. 3. Make sure your knees are locked throughout the whole movement. 4 5 Nice! Now repeat the same exercise on the other side. 1 2 3 4 5 Excellent!"
    cleaned = run_llama_cleaning(test_text)
    print("Result:\n", cleaned)
