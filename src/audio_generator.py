import os
import json
from elevenlabs.client import ElevenLabs
from elevenlabs import save

# --- Helper Functions (No changes here) ---

def load_elevenlabs_api_key():
    """Loads the ElevenLabs API key from the config file."""
    try:
        with open('../config/api_keys.json', 'r') as f:
            keys = json.load(f)
            return keys.get('elevenlabs_api_key')
    except Exception as e:
        print(f"Error loading API key: {e}")
        return None

def read_master_script(book_title, script_filename):
    """Reads the content of the master script file."""
    script_path = os.path.join('..', 'books', book_title, 'scripts', script_filename)
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            print(f"Successfully read master script from {script_path}")
            return f.read()
    except FileNotFoundError:
        print(f"Error: Master script file not found at {script_path}")
        return None

def split_script(text, max_chars=30000):
    """Splits the script into chunks under the character limit."""
    chunks = []
    current_pos = 0
    while current_pos < len(text):
        end_pos = min(current_pos + max_chars, len(text))
        if end_pos < len(text):
            split_point = text.rfind('\n\n', current_pos, end_pos)
            if split_point != -1:
                end_pos = split_point
        chunk = text[current_pos:end_pos].strip()
        if chunk:
            chunks.append(chunk)
        current_pos = end_pos
    print(f"Script split into {len(chunks)} chunks for audio generation.")
    return chunks

# --- Main Audio Generation Logic (Corrected) ---

def generate_audio_for_chunks(client, script_chunks, book_title):
    """Loops through script chunks and generates an audio file for each."""
    audio_dir = os.path.join('..', 'books', book_title, 'audio')
    os.makedirs(audio_dir, exist_ok=True)
    
    # The Voice ID for "Adam"
    ADAM_VOICE_ID = "AeRdCCKzvd23BpJoofzx"

    for i, chunk in enumerate(script_chunks):
        file_path = os.path.join(audio_dir, f"audio_part_{i+1}.mp3")
        print(f"\nGenerating audio for chunk {i+1}/{len(script_chunks)}...")
        
        try:
            # --- THIS IS THE CORRECTED METHOD CALL BASED ON YOUR DOCUMENTATION ---
            audio_stream = client.text_to_speech.convert(
                voice_id=ADAM_VOICE_ID,
                model_id="eleven_multilingual_v2", # This model is good for narration
                text=chunk
            )

            # The save function is designed to handle the audio stream
            save(audio_stream, file_path)
            
            print(f"--> Successfully saved chunk {i+1} to {file_path}")
        except Exception as e:
            print(f"--> Error generating audio for chunk {i+1}: {e}")
            break

# --- Main Execution (No changes here, TEST_MODE is still active) ---

if __name__ == "__main__":
    # --- !! TEST MODE FLAG !! ---
    TEST_MODE = True
    # ---------------------------

    BOOK_TITLE = "Meditations by Marcus Aurelius"
    SCRIPT_FILENAME = "Meditations by Marcus Aurelius_master_script.txt"

    print("--- Starting Audio Generation ---")
    if TEST_MODE:
        print("--- RUNNING IN TEST MODE ---")

    api_key = load_elevenlabs_api_key()
    if api_key:
        elevenlabs_client = ElevenLabs(api_key=api_key)
        master_script_text = read_master_script(BOOK_TITLE, SCRIPT_FILENAME)
        
        if master_script_text:
            script_chunks = split_script(master_script_text, max_chars=30000)
            
            if TEST_MODE and script_chunks:
                print("Test Mode: Selecting only the first chunk.")
                test_chunks = script_chunks[:1] 
                test_chunks[0] = test_chunks[0][:2000] 
                print(f"Test Mode: Truncated first chunk to {len(test_chunks[0])} characters.")
                generate_audio_for_chunks(elevenlabs_client, test_chunks, BOOK_TITLE)
            elif not TEST_MODE and script_chunks:
                generate_audio_for_chunks(elevenlabs_client, script_chunks, BOOK_TITLE)

            print("\n--- Audio generation process complete! ---")
        else:
            print("--- Halting: Could not read script file. ---")
    else:
        print("--- Halting: Could not load ElevenLabs API key. ---")