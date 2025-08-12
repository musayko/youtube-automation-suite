import os
import json
import glob
import random  # <-- Added the 'random' library
from natsort import natsorted

# --- Configuration ---
BOOK_TITLE = "Meditations by Marcus Aurelius"
BASE_DIR = os.path.join('..', 'books', BOOK_TITLE)
AUDIO_DIR = os.path.join(BASE_DIR, 'audio')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')
OVERLAYS_DIR = os.path.join('..', 'overlays')

def create_job_file():
    """
    Scans for all generated assets and creates a structured JSON file
    for a Premiere Pro ExtendScript (.jsx) to consume.
    """
    print("--- Starting Job File Creation ---")

    job_data = {
        "book_title": BOOK_TITLE,
        "assets": []
    }

    audio_files = natsorted(glob.glob(os.path.join(AUDIO_DIR, 'audio_part_*.mp3')))
    
    # --- UPDATED LOGIC TO SELECT A RANDOM OVERLAY ---
    overlay_files = glob.glob(os.path.join(OVERLAYS_DIR, '*.*'))
    default_overlay_path = "" # Default empty value

    if overlay_files:
        # If any overlay files are found, pick one at random
        chosen_overlay = random.choice(overlay_files)
        default_overlay_path = os.path.abspath(chosen_overlay)
        print(f"Randomly selected overlay: {os.path.basename(chosen_overlay)}")
    else:
        print("Warning: No overlay files found in the /overlays folder.")
    # ---------------------------------------------------

    if not audio_files:
        print("Error: No audio files found. Cannot create job file.")
        return

    print(f"Found {len(audio_files)} audio parts.")

    for i, audio_path in enumerate(audio_files):
        part_num = i + 1
        
        images = natsorted(glob.glob(os.path.join(IMAGES_DIR, f'image_part_{part_num}_img_*.png')))
        
        if not images:
            print(f"Warning: No images found for part {part_num}. This part will be skipped.")
            continue

        part_asset = {
            "part": part_num,
            "audio_path": os.path.abspath(audio_path),
            "image_paths": [os.path.abspath(img) for img in images],
            "overlay_path": default_overlay_path
        }
        job_data["assets"].append(part_asset)

    output_path = os.path.join(BASE_DIR, 'job.json')
    with open(output_path, 'w') as f:
        json.dump(job_data, f, indent=4)

    print(f"\nSuccess! Job file created at: {output_path}")
    print("This file contains all the necessary information for your Premiere Pro script.")

if __name__ == "__main__":
    create_job_file()