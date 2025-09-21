# main.py (New Hybrid Master Controller)

import sys
import os
import shutil
import glob
from natsort import natsorted
from src import config

# Add the 'src' directory to Python's path so we can import our scripts
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import the scripts from the 'src' folder
from src import master_script_generator
from src import audio_generator_gemini
from src import image_generator
from src import video_assembler

def setup_project_structure():
    """Checks and creates required folders, then cleans them for a fresh run."""
    print(f"--- Setting up project structure for '{config.BOOK_TITLE}' ---")
    required_dirs = [config.BOOK_DIR, config.CHUNKS_DIR, config.AUDIO_DIR, config.IMAGES_DIR, config.VIDEO_DIR]
    
    for dir_path in required_dirs:
        os.makedirs(dir_path, exist_ok=True)

    print("  > Clearing previous content (chunks, audio, images, video)...")
    if os.path.exists(config.CHUNKS_DIR): shutil.rmtree(config.CHUNKS_DIR)
    if os.path.exists(config.AUDIO_DIR): shutil.rmtree(config.AUDIO_DIR)
    if os.path.exists(config.IMAGES_DIR): shutil.rmtree(config.IMAGES_DIR)
    if os.path.exists(config.VIDEO_DIR): shutil.rmtree(config.VIDEO_DIR)
    
    for dir_path in required_dirs:
        os.makedirs(dir_path, exist_ok=True)
    print("--- Project structure is clean and ready. ---\n")


def run_pipeline():
    """Runs the entire video creation pipeline with a user choice for audio generation."""
    
    # Phase 0: Always clean and set up the project
    setup_project_structure()
    
    # Phase 1: Always generate the script chunks
    print("--- [PHASE 1 of 4] Executing Script Generator ---")
    master_script_generator.main()
    chunk_files = natsorted(glob.glob(os.path.join(config.CHUNKS_DIR, 'chunk_*.txt')))
    if not chunk_files:
        print("❌ CRITICAL ERROR: Script generation failed. No chunk files created. Halting.")
        return
    print("--- [PHASE 1] Complete ---\n")
    
    # --- NEW: User Choice for Audio Generation ---
    print("--- [PHASE 2 of 4] Audio Generation ---")
    choice = input("Do you want to generate audio automatically with the Gemini API? (y/n): ").lower().strip()

    if choice == 'y':
        print("\n> Automatic generation selected. Executing Audio Generator...")
        audio_generator_gemini.main()
    else:
        print("\n> Manual audio generation selected. Please follow these instructions:")
        print("-" * 50)
        print(f"1. Open the folder: {config.CHUNKS_DIR}")
        print(f"   You will find {len(chunk_files)} text files (chunk_01.txt, chunk_02.txt, etc.).")
        print("\n2. For each text file, record your narration using your preferred tool (e.g., Audacity, AI Studio).")
        print("\n3. IMPORTANT: Save each audio file as a WAV file with the EXACT corresponding name.")
        print("   - Narration for 'chunk_01.txt' MUST be saved as 'audio_part_01.wav'")
        print("   - Narration for 'chunk_02.txt' MUST be saved as 'audio_part_02.wav'")
        print("   - ...and so on.")
        print(f"\n4. Place all your final .wav files into this folder: {config.AUDIO_DIR}")
        print("-" * 50)
        input("\nPress Enter when you have finished placing all your audio files...")

    print("--- [PHASE 2] Complete ---\n")
    # ---------------------------------------------

    # Phase 3: Generate Images (This will work regardless of audio source)
    print("--- [PHASE 3 of 4] Executing Image Generator ---")
    image_generator.main()
    print("--- [PHASE 3] Complete ---\n")

    # Phase 4: Assemble Final Video
    print("--- [PHASE 4 of 4] Executing Video Assembler ---")
    video_assembler.main()
    print("--- [PHASE 4] Complete ---\n")
    
    print("🎉🎉🎉 --- PIPELINE COMPLETE! --- 🎉🎉🎉")
    print(f"Final video for '{config.BOOK_TITLE}' should be in the book's 'video' directory.")


if __name__ == "__main__":
    run_pipeline()