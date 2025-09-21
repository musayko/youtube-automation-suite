import os
import json
import sys
from elevenlabs.client import ElevenLabs
from elevenlabs import save

# Add the parent directory to the Python path to find the 'config' module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# --- Helper Functions ---

def load_elevenlabs_api_key():
    """Loads the ElevenLabs API key from the config file."""
    api_key_path = os.path.join(config.CONFIG_DIR, 'api_keys.json')
    try:
        with open(api_key_path, 'r') as f:
            keys = json.load(f)
            return keys.get('elevenlabs_api_key')
    except Exception as e:
        print(f"Error loading API key from {api_key_path}: {e}")
        return None

def get_script_chunks_from_files():
    """
    Scans the chunks directory, reads each .txt file, and returns a sorted list
    of tuples containing the base filename and its content.
    """
    chunks_dir = config.CHUNKS_DIR
    if not os.path.isdir(chunks_dir):
        print(f"Error: Chunks directory not found at {chunks_dir}")
        return []

    chunks = []
    # Get all .txt files and sort them numerically
    try:
        filenames = sorted(
            [f for f in os.listdir(chunks_dir) if f.endswith('.txt')],
            key=lambda f: int(''.join(filter(str.isdigit, f)) or 0)
        )
    except ValueError:
        print(f"Warning: Could not sort files numerically. Using alphabetical sort.")
        filenames = sorted([f for f in os.listdir(chunks_dir) if f.endswith('.txt')])


    print(f"Found {len(filenames)} chunk files in {chunks_dir}")

    for filename in filenames:
        file_path = os.path.join(chunks_dir, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Get the filename without the .txt extension
                basename = os.path.splitext(filename)[0]
                chunks.append((basename, content))
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
    return chunks

# --- Main Audio Generation Logic ---

def generate_audio_for_chunks(client, script_chunks):
    """
    Loops through script chunks from files and generates a matching audio file for each.
    """
    os.makedirs(config.AUDIO_DIR, exist_ok=True)
    
    # The Voice ID for "Adam"
    ADAM_VOICE_ID = "AeRdCCKzvd23BpJoofzx"

    total_chunks = len(script_chunks)
    for i, (basename, text_chunk) in enumerate(script_chunks):
        # Name the output mp3 file to match the input txt file
        file_path = os.path.join(config.AUDIO_DIR, f"{basename}.mp3")
        
        print(f"\n[{i+1}/{total_chunks}] Generating audio for '{basename}.txt'...")
        
        # --- Check if the audio file already exists to avoid re-generating ---
        if os.path.exists(file_path):
            print(f"--> Audio file already exists at {file_path}. Skipping.")
            continue

        try:
            audio_stream = client.text_to_speech.convert(
                voice_id=ADAM_VOICE_ID,
                model_id="eleven_multilingual_v2",
                text=text_chunk
            )
            save(audio_stream, file_path)
            print(f"--> Successfully saved audio to {file_path}")
        except Exception as e:
            print(f"--> Error generating audio for {basename}.txt: {e}")
            break # Stop on first error

# --- Main Execution ---

if __name__ == "__main__":
    # --- !! TEST MODE FLAG !! ---
    # Set to a number to process only the first N chunks. Set to False for all.
    TEST_MODE = 10
    # ---------------------------

    print("--- Starting Audio Generation (from chunk files) ---")
    print(f"Book Title: {config.BOOK_TITLE}")
    if TEST_MODE:
        print(f"--- RUNNING IN TEST MODE (Processing first {TEST_MODE} chunk(s)) ---")

    api_key = load_elevenlabs_api_key()
    if api_key:
        elevenlabs_client = ElevenLabs(api_key=api_key)
        
        # This function replaces read_master_script and split_script
        script_chunks = get_script_chunks_from_files()
        
        if script_chunks:
            chunks_to_process = script_chunks
            if TEST_MODE:
                chunks_to_process = script_chunks[:TEST_MODE]
                print(f"Test Mode: Selected {len(chunks_to_process)} chunk(s) to process.")
            
            generate_audio_for_chunks(elevenlabs_client, chunks_to_process)
            print("\n--- Audio generation process complete! ---")
        else:
            print("--- Halting: No script chunk files were found. ---")
    else:
        print("--- Halting: Could not load ElevenLabs API key. ---")