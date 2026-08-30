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
Replace every standalone digit (e.g. 1, 2, 3...) in the following physical therapy text with its full English word (e.g. one, two, three).
Rules:
- Only replace digits that appear as separate words, not part of time stamps, measurements, or decimals.
- DO NOT change punctuation, words, symbols, or formatting.
- DO NOT add any explanations, formatting, or numbering.
- Return ONLY the modified text (no intro, no comments).

Text:
\"\"\"{original_text}\"\"\"
"""

    output_1 = run_prompt_llama(prompt_1)

    # Step 2: Rewrite the instructions for clarity and professionalism, preserving all numbers and their order
    prompt_2 = f"""
Rewrite the following physical therapy instructions in **clear, professional English**.

Rules:
- Every instruction must be a **complete sentence** with a clear subject and verb.
- Maintain the **original order** of sentences and numbers. DO NOT remove, merge, reorder, or reinterpret them.
- Keep all counting sequences (e.g. "one two three") **exactly as they appear**.
- DO NOT replace or change technical terms like: "Smart View", "Smart TV", "Casting", or other interface elements.
- DO NOT add or remove any punctuation marks.
- Avoid repeating words unless they were repeated in the original.
- Output only the rewritten instructions. DO NOT add explanations or headings.

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
