import re
from math import ceil

def map_text_to_timestamps_anylang(translated_text: str, eng_timestamps_file: str, output_file: str):
    # --- Step 1: Read timestamps from the English file ---
    print("[Level 1] Step 1: Reading timestamps from the English file...")
    with open(eng_timestamps_file, encoding="utf-8") as f:
        eng_lines = f.readlines()
    print(f"[Level 2] Read {len(eng_lines)} lines from {eng_timestamps_file}")

    timestamps = []
    for idx, line in enumerate(eng_lines):
        # גמיש יותר עם רווחים אם צריך:
        m = re.match(r"\[(\d+:\d+:\d+\.\d+)\s*-->\s*(\d+:\d+:\d+\.\d+)]", line)
        if m:
            start, end = m.groups()
            timestamps.append((start, end))
            print(f"[Level 3] Parsed timestamp {start} --> {end} from line {idx+1}")

    print(f"[Level 2] Total valid timestamps found: {len(timestamps)}")

    # --- Step 2: Split the translated text into clean lines ---
    print("[Level 1] Step 2: Splitting translated text into clean lines...")
    split_lines = [l.strip() for l in translated_text.split('\n') if l.strip()]
    print(f"[Level 2] Total non-empty translated lines: {len(split_lines)}")

    if not timestamps:
        print("[Level 1] No valid timestamps found in the file. Exiting function.")
        return

    # --- Step 3: Distribute the lines evenly across the timestamps ---
    print("[Level 1] Step 3: Distributing lines evenly across timestamps...")
    num_timestamps = len(timestamps)
    chunk_size = ceil(len(split_lines) / num_timestamps)
    print(f"[Level 2] Number of timestamps: {num_timestamps}")
    print(f"[Level 2] Calculated chunk size: {chunk_size}")

    chunks = [
        " ".join(split_lines[i:i + chunk_size])
        for i in range(0, len(split_lines), chunk_size)
    ]
    print(f"[Level 2] Created {len(chunks)} chunks of text.")

    output_lines = []
    for i, (start, end) in enumerate(timestamps):
        text = chunks[i] if i < len(chunks) else ""
        output_lines.append(f"[{start} --> {end}] {text}")
        print(f"[Level 3] Output line {i+1}: [{start} --> {end}] {text[:30]}{'...' if len(text) > 30 else ''}")

    # --- Step 4: Write to the final output file ---
    print("[Level 1] Step 4: Writing to the final output file...")
    with open(output_file, "w", encoding="utf-8") as f:
        for idx, line in enumerate(output_lines):
            f.write(line + "\n")
            print(f"[Level 3] Wrote line {idx+1} to output file.")

    print(f"[Level 1] Created file {output_file} with timestamps and aligned text.")
