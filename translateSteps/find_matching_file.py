import re
from pipeline_config import AUDIO_DIR, HEBREW_VIDEO_DIR

def extract_number(filename):
    """
    Extracts the first sequence of digits found in the filename.
    Returns the number as an integer, or None if no digits are found.
    """
    match = re.search(r'(\d+)', filename)
    return int(match.group(1)) if match else None

def find_matching_number_in_hebvideo():
    """
    Finds the most recently modified file in the 'audiofile' directory,
    extracts the number from its filename, and checks if a file with the same
    number exists in the 'HebVideo' directory.

    Returns:
        (bool, int or None, str or None):
            - True and the matching filename if found,
            - False and the extracted number if not found,
            - None for number and filename if directories or files are missing.
    """
    # Get the base directory (directory of this script)
    audio_done_dir = AUDIO_DIR
    heb_videos_dir = HEBREW_VIDEO_DIR

    # Check if the audiofile directory exists
    if not audio_done_dir.exists():
        print(f"Directory not found: {audio_done_dir}")
        return False, None, None

    # Check if the HebVideo directory exists
    if not heb_videos_dir.exists():
        print(f"Directory not found: {heb_videos_dir}")
        return False, None, None

    # List all files in the audiofile directory
    files = [f for f in audio_done_dir.iterdir() if f.is_file()]
    if not files:
        print("No files found in audiofile directory.")
        return False, None, None

    # Find the most recently modified file
    latest_file = max(files, key=lambda f: f.stat().st_mtime)
    latest_filename = latest_file.name
    # Extract the number from the latest file's name
    latest_number = extract_number(latest_filename)
    print(f"Most recent file: {latest_filename} | Extracted number: {latest_number}")

    if latest_number is None:
        print("No number found in the latest file's name.")
        return False, None, None

    # Search for a file in HebVideo with the same number
    for path in heb_videos_dir.iterdir():
        if not path.is_file():
            continue
        fname = path.name
        number = extract_number(fname)
        print(f"Checking file: {fname} | Number: {number}")
        if number == latest_number:
            print("Found! Matching file exists in HebVideo:", fname)
            return True, latest_number, fname

    print("No matching file found in HebVideo.")
    return False, latest_number, None

# Example usage:
if __name__ == "__main__":
    success, number, match_name = find_matching_number_in_hebvideo()
    if success:
        print(f"Success! Found file with number {number}: {match_name}")
    else:
        print(f"Failure. Latest number: {number}. No match found.")
