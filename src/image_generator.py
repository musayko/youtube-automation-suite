# src/image_generator.py (Final Version with Correct JSON Parsing)

import os
import json
import time
import glob
import google.genai as genai
from google.genai import types
from PIL import Image
from io import BytesIO
from natsort import natsorted
import config

# --- HELPER FUNCTIONS (No Changes) ---

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

def create_dynamic_example_prompt(config):
    """
    Creates a style-appropriate example prompt to guide the AI.
    This is the key to making the system work for ANY book style.
    """
    style_details = config.get('style_details', {})
    text_preference = config.get('image_text_preference', 'text okay')
    
    # Universal concept for the example: "Confusion vs. Clarity"
    concept_scene = "a tangled, chaotic jumble of lines representing confusion, contrasted with a single, elegant, clear line representing clarity"

    # Get style specifics
    primary_style = style_details.get('primary_style', 'A high-quality image')
    technique = style_details.get('technique', 'created with expert technique')
    palette = style_details.get('palette', 'using a suitable color palette')
    
    text_instruction = ""
    if text_preference == 'no text':
        text_instruction = "The final image MUST NOT contain any text, letters, or numbers."

    # Assemble the dynamic example
    example_prompt = (
        f'"{primary_style} of {concept_scene}. {technique}. The palette is {palette}, with a specific '
        f'highlight color used to emphasize the clear line. {text_instruction}"'
    )
    return example_prompt

def generate_contextual_image_prompts(text_chunk, book_style_config, client, num_images, part_number, total_parts):
    """
    Generates hyper-consistent prompts by dynamically creating the instructions and examples
    based on the current book's specific style guide.
    """
    print(f"  > Generating {num_images} contextual prompts for part {part_number}/{total_parts}...")
    
    # --- DYNAMIC SETUP ---
    style_details = book_style_config.get('style_details', {})
    text_preference = book_style_config.get('image_text_preference', 'text okay')
    
    text_instruction_for_final_image = ""
    if text_preference == 'no text':
        text_instruction_for_final_image = "The final image MUST NOT contain any text, letters, or numbers."

    # Dynamically create the required structure for the AI to follow
    required_structure = (
        f'"{style_details.get("primary_style", "")} of [a specific, concrete scene from the text]. '
        f'{style_details.get("technique", "")}. '
        f'The palette is {style_details.get("palette", "")}. '
        f'{text_instruction_for_final_image}"'
    )

    # Dynamically create a perfect example prompt that matches the current style
    dynamic_example = create_dynamic_example_prompt(book_style_config)
    # --- END DYNAMIC SETUP ---

    style_prompt = f"""
    You are an expert art director who creates hyper-consistent image prompts. Your ONLY output must be a valid JSON array of {num_images} strings. Do not add ```json``` or any commentary.

    **CRITICAL TASK:** Your job is to generate prompts that are incredibly consistent. To do this, you MUST follow the "Required Output Prompt Structure" below for every single prompt. You will combine a scene from the text with the precise language from the style guide. Do not deviate.

    **Visual Style Guide (for your reference):**
    - Primary Style: {style_details.get('primary_style', 'N/A')}
    - Technique: {style_details.get('technique', 'N/A')}
    - Palette: {style_details.get('palette', 'N/A')}

    **Text for this Part:**
    {text_chunk[:2000]}

    **Required Output Prompt Structure:**
    Each of the {num_images} prompts you generate MUST be a single string following this exact structure:
    {required_structure}

    **Example of a PERFECTLY structured prompt (for this specific style):**
    {dynamic_example}

    Now, generate the JSON array based on the text provided.
    """
    
    try:
        response = client.models.generate_content(
            # Using a more capable model is recommended for complex, structured instructions
            model='gemini-2.5-flash-lite', 
            contents=[style_prompt]
        )
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        image_prompts = json.loads(cleaned_response)
        
        if len(image_prompts) != num_images:
            print(f"  > Warning: Expected {num_images} prompts, got {len(image_prompts)}")
        
        print(f"  > Generated {len(image_prompts)} DYNAMICALLY-STYLED contextual prompts.")
        return image_prompts
    except Exception as e:
        print(f"  > Error generating prompts: {e}")
        print(f"  > Raw response was: {response.text}")
        return []
def generate_and_save_images(client, image_prompts, part_number):
    """Generates and saves images using Imagen."""
    if not image_prompts: return False
    os.makedirs(config.IMAGES_DIR, exist_ok=True)
    success_count = 0
    for i, item in enumerate(image_prompts):
        final_prompt = ""
        if isinstance(item, str):
            final_prompt = item
        elif isinstance(item, dict) and 'prompt' in item:
            final_prompt = item['prompt']
        else:
            print(f"    >> ✗ Error: Unrecognized prompt format for image {i+1}. Skipping.")
            continue

        filename = os.path.join(config.IMAGES_DIR, f"image_part_{part_number}_img_{i+1}.png")
        print(f"    >> Generating image {i+1}/{len(image_prompts)} for part {part_number}")
        try:
            response = client.models.generate_images(
                model='models/imagen-3.0-generate-002', prompt=final_prompt,
                config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="16:9")
            )
            for generated_image in response.generated_images:
                image_data = generated_image.image.image_bytes
                Image.open(BytesIO(image_data)).save(filename)
                print(f"    >> ✓ Saved: {filename}")
                success_count += 1
        except Exception as e:
            if "RESOURCE_EXHAUSTED" in str(e):
                print("    >> ✗ Hit API rate limit. Pausing for 60 seconds.")
                time.sleep(60)
            else:
                print(f"    >> ✗ An unknown error occurred: {e}")
            continue
        if i < len(image_prompts) - 1:
            time.sleep(5)
    print(f"    >> Part {part_number} complete: {success_count}/{len(image_prompts)} images generated")
    return success_count > 0

def main():
    """Main function that reads text chunks and generates corresponding images."""
    TEST_MODE = False
    NUM_IMAGES_PER_PART = 5

    print(f"=== Dynamic Image Generation for '{config.BOOK_TITLE}' ===")
    
    api_keys, visual_styles = load_configs()
    if not api_keys or not visual_styles: return
    
    book_style = visual_styles.get(config.BOOK_TITLE)
    if not book_style:
        print(f"Error: No visual style found for '{config.BOOK_TITLE}'.")
        return
    
    try:
        client = genai.Client(api_key=api_keys['google_api_key'])
        print("✓ Google GenAI Client initialized successfully.")
    except Exception as e:
        print(f"✗ Failed to create GenAI Client: {e}")
        return

    chunk_files = natsorted(glob.glob(os.path.join(config.CHUNKS_DIR, 'chunk_*.txt')))
    if not chunk_files:
        print(f"FATAL ERROR: No chunk files found in {config.CHUNKS_DIR}.")
        return

    parts_to_process = chunk_files
    if TEST_MODE: parts_to_process = chunk_files[:3]
    
    print(f"\n--- Found {len(chunk_files)} text chunks. Starting image generation. ---")

    for chunk_path in parts_to_process:
        part_num_str = os.path.basename(chunk_path).replace('chunk_', '').replace('.txt', '')
        print(f"\n--- Checking Part {part_num_str}/{len(chunk_files)} ---")

        image_search_pattern = os.path.join(config.IMAGES_DIR, f'image_part_{part_num_str}_img_*.png')
        existing_images = glob.glob(image_search_pattern)
        
        if existing_images:
            user_input = input(f"  > Found {len(existing_images)} images. Regenerate? (y/n): ").lower()
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
        
        time.sleep(5)

    print("\n\n=== Image Generation Complete! ===")

if __name__ == "__main__":
    main()