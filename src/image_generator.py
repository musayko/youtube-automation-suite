import os
import json
import time
import glob
import google.genai as genai
from google.genai import types
from PIL import Image
from io import BytesIO
from natsort import natsorted
import config  # Use our new central config file

def load_configs():
    """Loads API keys and visual style configurations."""
    try:
        config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
        with open(os.path.join(config_dir, 'api_keys.json'), 'r') as f:
            api_keys = json.load(f)
        with open(os.path.join(config_dir, 'book_visual_styles.json'), 'r') as f:
            visual_styles = json.load(f)
        return api_keys, visual_styles
    except Exception as e:
        print(f"Error loading configuration files: {e}")
        return None, None

def generate_contextual_image_prompts(text_chunk, book_style_config, client, num_images, part_number, total_parts):
    """
    Enhanced prompt generation that creates contextually relevant images
    and respects text preferences from the style config.
    """
    print(f"  > Generating {num_images} contextual prompts for part {part_number}/{total_parts}...")
    
    text_preference = book_style_config.get('image_text_preference', 'text okay')
    
    text_instruction = ""
    if text_preference == 'no text':
        text_instruction = "5. CRITICAL: The generated image must NOT contain any text, letters, words, or numbers whatsoever."

    style_prompt = f"""
    You are creating visual accompaniments for an audiobook.

    BOOK CONTEXT:
    - This is part {part_number} of {total_parts} total parts
    - Visual Style: {book_style_config['style']}
    - Themes: {', '.join(book_style_config['themes'])}

    TEXT FOR THIS PART:
    {text_chunk}

    Create {num_images} distinct, high-quality **image prompts** that follow these rules:
    1. Directly relate to the key concepts in this specific text segment.
    2. Progress visually to complement the narration flow.
    3. Are suitable for 16:9 aspect ratio video.
    4. Match the overall book's visual style and themes.
    5. Don't include any text
    {text_instruction} 

    Output ONLY a valid JSON array of {num_images} descriptive prompt STRINGS.
    """
    
    try:
        response = client.models.generate_content(
            model='models/gemini-2.5-flash-lite',
            contents=[style_prompt]
        )
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        image_prompts = json.loads(cleaned_response)
        
        if len(image_prompts) != num_images:
            print(f"  > Warning: Expected {num_images} prompts, got {len(image_prompts)}")
        
        print(f"  > Generated {len(image_prompts)} contextual prompts (Text preference: '{text_preference}').")
        return image_prompts
    except Exception as e:
        print(f"  > Error generating prompts: {e}")
        return []

def generate_and_save_images(client, image_prompts, part_number):
    """
    Generates and saves images using Imagen, with added pauses and robust
    handling for incorrectly formatted prompts from the LLM.
    """
    if not image_prompts:
        print("    >> No image prompts provided, skipping image generation.")
        return False

    os.makedirs(config.IMAGES_DIR, exist_ok=True)

    success_count = 0
    for i, item in enumerate(image_prompts):
        
        # --- FIX for Pydantic Error: Check the prompt format before using it ---
        final_prompt = ""
        if isinstance(item, str):
            final_prompt = item
        elif isinstance(item, dict) and 'prompt' in item:
            print(f"    >> (Note: Corrected a malformed prompt from the AI for image {i+1})")
            final_prompt = item['prompt']
        else:
            print(f"    >> ✗ Error: Unrecognized prompt format for image {i+1}. Skipping. Data: {item}")
            continue
        # --------------------------------------------------------------------

        filename = os.path.join(config.IMAGES_DIR, f"image_part_{part_number}_img_{i+1}.png")
        print(f"    >> Generating image {i+1}/{len(image_prompts)} for part {part_number}")
        
        try:
            response = client.models.generate_images(
                model='models/imagen-3.0-generate-002',
                prompt=final_prompt, # Use the corrected, guaranteed-to-be-string variable
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9",
                )
            )

            for generated_image in response.generated_images:
                image_data = generated_image.image.image_bytes
                image = Image.open(BytesIO(image_data))
                image.save(filename)
                print(f"    >> ✓ Saved: {filename}")
                success_count += 1

        except Exception as e:
            error_message = str(e)
            if "RESOURCE_EXHAUSTED" in error_message or "Quota" in error_message:
                print("    >> ✗ Hit API rate limit. Pausing for 60 seconds before continuing...")
                time.sleep(60)
            else:
                print(f"    >> ✗ An unknown error occurred generating image {i+1}: {e}")
            continue

        # Add a pause AFTER each successful image generation to respect rate limits
        if i < len(image_prompts) - 1: # Don't sleep after the last image of the part
            print("    >> Pausing for 5 seconds...")
            time.sleep(5)

    print(f"    >> Part {part_number} complete: {success_count}/{len(image_prompts)} images generated")
    return success_count > 0

def main():
    """
    Main function that reads text chunks and generates corresponding images,
    intelligently skipping parts that are already complete.
    """
    TEST_MODE = False
    NUM_IMAGES_PER_PART = 5

    print(f"=== Dynamic Image Generation for '{config.BOOK_TITLE}' ===")
    
    api_keys, visual_styles = load_configs()
    if not api_keys or not visual_styles:
        print("Halting: Configuration files are missing or invalid.")
        return
    
    book_style = visual_styles.get(config.BOOK_TITLE)
    if not book_style:
        print(f"Error: No visual style found for '{config.BOOK_TITLE}' in book_visual_styles.json.")
        return
    
    try:
        client = genai.Client(api_key=api_keys['google_api_key'])
        print("✓ Google GenAI Client initialized successfully.")
    except Exception as e:
        print(f"✗ Failed to create GenAI Client: {e}")
        return

    # Find the text chunks to process (our "single source of truth")
    chunk_files = natsorted(glob.glob(os.path.join(config.CHUNKS_DIR, 'chunk_*.txt')))
    if not chunk_files:
        print(f"FATAL ERROR: No chunk files found in {config.CHUNKS_DIR}")
        print("Please run master_script_generator.py first.")
        return

    parts_to_process = chunk_files
    if TEST_MODE:
        parts_to_process = chunk_files[:3]
        print(f"\n--- TEST MODE: Processing only first {len(parts_to_process)} parts ---")
    
    print(f"\n--- Found {len(chunk_files)} text chunks. Starting image generation. ---")

    for chunk_path in parts_to_process:
        part_num_str = os.path.basename(chunk_path).replace('chunk_', '').replace('.txt', '')
        print(f"\n--- Checking Part {part_num_str}/{len(chunk_files)} ---")

        # Skip if images already exist
        image_search_pattern = os.path.join(config.IMAGES_DIR, f'image_part_{part_num_str}_img_*.png')
        existing_images = glob.glob(image_search_pattern)
        
        if existing_images:
            print(f"  > Found {len(existing_images)} existing images for part {part_num_str}.")
            user_input = input("  > Do you want to regenerate them? (y/n): ").lower()
            if user_input != 'y':
                print(f"  > Skipping part {part_num_str}.")
                continue
        
        print(f"--- Processing Part {part_num_str} ---")
        with open(chunk_path, 'r', encoding='utf-8') as f:
            text_for_prompts = f.read()
        
        image_prompts = generate_contextual_image_prompts(
            text_for_prompts, book_style, client, NUM_IMAGES_PER_PART, part_num_str, len(chunk_files)
        )
        if image_prompts:
            generate_and_save_images(client, image_prompts, part_num_str)
        
        # This is a longer pause between entire parts
        time.sleep(5)

    print("\n\n=== Image Generation Complete! ===")

if __name__ == "__main__":
    main()