# src/audio_generator_gemini.py (Final Corrected Version)
import os
import json
import glob
import google.genai as genai
from google.genai import types
import wave
from natsort import natsorted
import config

# --- Helper function from the documentation to save WAV files ---
def save_wav_file(filename, pcm_data, channels=1, sample_width=2, framerate=24000):
    """Saves PCM audio data to a WAV file."""
    try:
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(framerate)
            wf.writeframes(pcm_data)
        return True
    except Exception as e:
        print(f"  > Error saving WAV file: {e}")
        return False

# --- Helper functions from our previous scripts ---
def load_api_key():
    """Loads the Google API key from the config file."""
    try:
        with open('../config/api_keys.json', 'r') as f:
            keys = json.load(f)
            return keys.get('google_api_key')
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

def split_script(text, max_chars=4000):
    """
    Splits the script into chunks safely under the Gemini API character limit for TTS.
    """
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

# --- Main Audio Generation Logic using Gemini TTS ---
def generate_audio_for_chunks(client, script_chunks, book_title):
    """Loops through script chunks and generates a WAV audio file for each."""
    audio_dir = os.path.join('..', 'books', book_title, 'audio')
    os.makedirs(audio_dir, exist_ok=True)
    
    for i, chunk in enumerate(script_chunks):
        file_path = os.path.join(audio_dir, f"audio_part_{i+1}.wav")
        print(f"\nGenerating audio for chunk {i+1}/{len(script_chunks)}...")
        
        try:
            prompt_text = f"Say in a calm, gentle audiobook narration: {chunk}"
            
            tts_config = types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name='Algieba'
                        )
                    )
                )
            )

            response = client.models.generate_content(
                model="models/gemini-2.5-pro-preview-tts",
                contents=[prompt_text],
                config=tts_config
            )

            # --- NEW, ROBUST ERROR CHECKING ---
            # First, check if the response was blocked or is empty
            if not response.candidates:
                reason = "Unknown reason"
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    reason = response.prompt_feedback.block_reason
                print(f"--> WARNING: Chunk {i+1} was blocked by API safety filters (Reason: {reason}). Skipping.")
                continue # Move to the next chunk

            # If not blocked, proceed to get the audio data
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            if save_wav_file(file_path, audio_data):
                print(f"--> Successfully saved chunk {i+1} to {file_path}")

        except Exception as e:
            print(f"--> Error generating audio for chunk {i+1}: {e}")
            continue # Continue to the next chunk even if there's an error

# --- Main Execution ---
if __name__ == "__main__":
    print("--- Starting Audio Generation with Gemini TTS ---")

    # 1. Load the API key
    api_key = load_api_key()
    if not api_key:
        print("--- Halting: Could not load Google API key. ---")
    else:
        gemini_client = genai.Client(api_key=api_key)
        
        # 2. Find all the chunk files created by the master script generator
        chunk_files = natsorted(glob.glob(os.path.join(config.CHUNKS_DIR, 'chunk_*.txt')))

        if not chunk_files:
            print(f"FATAL ERROR: No chunk files found in {config.CHUNKS_DIR}")
            print("Please run master_script_generator.py first.")
        else:
            os.makedirs(config.AUDIO_DIR, exist_ok=True)
            print(f"Found {len(chunk_files)} text chunks. Starting audio generation for '{config.BOOK_TITLE}'.")

            # 3. Loop through each chunk file
            for chunk_path in chunk_files:
                # Determine the correct output file name from the chunk name
                part_num_str = os.path.basename(chunk_path).replace('chunk_', '').replace('.txt', '')
                audio_path = os.path.join(config.AUDIO_DIR, f"audio_part_{part_num_str}.wav")
                
                print(f"\n--- Processing Part {part_num_str}/{len(chunk_files)} ---")

                # 4. Skip if the audio file already exists
                if os.path.exists(audio_path):
                    print(f"  > Audio file already exists. Skipping.")
                    continue

                # 5. Read the text from the chunk file
                with open(chunk_path, 'r', encoding='utf-8') as f:
                    text_to_speak = f.read()

                # 6. Generate audio for that chunk
                try:
                    prompt_text = f"Read in a calm, gentle audiobook narration: {text_to_speak}"
                    
                    tts_config = types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Algieba')
                            )
                        )
                    )

                    response = gemini_client.models.generate_content(
                        model="gemini-2.5-pro-preview-tts", contents=[prompt_text], config=tts_config
                    )

                    if not response.candidates:
                        reason = response.prompt_feedback.block_reason if response.prompt_feedback else "Unknown"
                        print(f"--> WARNING: Chunk was blocked by API (Reason: {reason}). Skipping.")
                        continue

                    audio_data = response.candidates[0].content.parts[0].inline_data.data
                    if save_wav_file(audio_path, audio_data):
                        print(f"--> Successfully saved audio for part {part_num_str}")

                except Exception as e:
                    print(f"--> Error generating audio for chunk {part_num_str}: {e}")
            
            print("\n--- Audio generation process complete! ---")