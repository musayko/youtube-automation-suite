# --- START OF FILE historical_script_generator.py (Revised for Versatility) ---

import os
import json
import time
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import google.generativeai as genai
import config # Use our new central config file

INTRO_TEMPLATE = """
Welcome to Nocturnal Knowledge.

Tonight, we're exploring the history detailed in "{book_title}" by {author}.

Settle in as we journey through the pivotal events and figures that shaped our world. If you enjoy this exploration, 
please consider liking this video and subscribing for more deep dives into history's most compelling stories.

Our journey begins now.
"""

# --- Helper Functions ---

def get_book_text(epub_path):
    """Opens an EPUB file and extracts all readable text content."""
    print(f"Reading and parsing EPUB file from: {epub_path}")
    try:
        book = epub.read_epub(epub_path)
        full_text = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            # Extract text and clean up whitespace
            text = ' '.join(soup.get_text().split())
            if text:
                full_text.append(text)
        print(f"Successfully extracted text from EPUB. Found {len(full_text)} content items.")
        return "\n\n".join(full_text)
    except FileNotFoundError:
        print(f"Error: EPUB file not found at {epub_path}")
        return None
    except Exception as e:
        print(f"An error occurred while parsing the EPUB: {e}")
        return None

def load_api_key():
    """Loads the Google API key from the config file."""
    try:
        # Assumes config directory is one level up from the script's directory
        config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
        api_keys_path = os.path.join(config_dir, 'api_keys.json')
        if not os.path.exists(api_keys_path):
            print(f"Error: api_keys.json not found at {api_keys_path}. Please create it.")
            return None
        with open(api_keys_path, 'r') as f:
            keys = json.load(f)
            google_key = keys.get('google_api_key')
            if not google_key:
                print("Error: 'google_api_key' not found in api_keys.json.")
                return None
            return google_key
    except FileNotFoundError:
        print("Error: Configuration directory or api_keys.json not found.")
        return None
    except json.JSONDecodeError:
        print("Error: Could not parse api_keys.json. Ensure it's valid JSON.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred loading API key: {e}")
        return None

# --- Phase 1: Generate Outline ---

def generate_historical_outline(book_text, book_title, model):
    """Creates a logical outline based on the book's structure, which may be chronological or thematic."""
    print("Phase 1: Generating Flexible Historical Outline...")
    
    prompt = f"""
    You are a historical documentary producer creating a factual outline for a 1-hour Youtube documentary narration based on the book "{book_title}".

    Analyze the full book text and create a logical outline based on the book's primary structure, whether it is chronological or thematic.
    
    The output MUST be a JSON object with this structure:
    {{
        "main_sections": [
            {{
                "title": "Main Section Title (This could be a historical era OR a theme, e.g., 'The Rise of Naval Power')",
                "subtopics": [
                    "Specific Event/Figure 1 (e.g., 'The Battle of Trafalgar')",
                    "Key Turning Point 2 (e.g., 'The Development of the Ironclad')",
                    "Major Consequence 3 (e.g., 'The Decline of Piracy')"
                ]
            }}
        ]
    }}

    Guidelines:
    - Determine if the book is chronological or thematic and structure the outline accordingly.
    - Create 6-12 detailed subtopics in total, distributed logically across the main sections, to fill a 1-hour documentary.
    - Each subtopic should represent a distinct, narratable point or event.
    - Focus on factual accuracy and historical significance as presented in the book.

    Here is the full book text for your analysis: --- {book_text} ---
    """
    
    try:
        response = model.generate_content(prompt)
        # Ensure response text is not None before attempting to strip/replace
        if response and response.text:
            cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
            outline_data = json.loads(cleaned_response)
            
            print("Successfully generated flexible outline:")
            for section in outline_data.get('main_sections', []):
                print(f"- {section.get('title', 'Unknown Section')}")
                for subtopic in section.get('subtopics', []):
                    print(f"  - {subtopic}")
            return outline_data
        else:
            print("  > Warning: Received empty or invalid response for outline generation.")
            return None
    except json.JSONDecodeError:
        print("  > Error: Failed to parse JSON response from AI.")
        print(f"  > Raw response: {response.text if response and response.text else 'Empty response'}")
        return None
    except Exception as e:
        print(f"  > An error occurred during outline generation: {e}")
        return None

# --- Phase 2: Generate ONE Substantial, Self-Contained Script Chunk ---

def generate_historical_chunk(book_text, book_title, main_section_title, sub_topic_title, model):
    """
    Generates ONE single, self-contained, and detailed narration script for a subtopic.
    It does NOT include transitions.
    """
    print(f"  > Phase 2: Writing self-contained script for sub-topic: '{sub_topic_title}'...")
    
    # --- MODIFIED PROMPT TO INCLUDE TARGET LENGTH ---
    prompt = f"""
    You are a historical documentarian writing a deep, engaging narration for a segment of a documentary.
    Your task is to write a single, comprehensive, and self-contained script explaining the sub-topic "{sub_topic_title}", which is part of the larger section "{main_section_title}" from the book "{book_title}".

    **CRITICAL INSTRUCTIONS:**
    1.  **NARRATION ONLY:** Your output must ONLY be the words to be spoken by the narrator.
    2.  **NO PRODUCTION NOTES:** DO NOT include any camera directions, sound effect cues, visual clues, or notes like "[pause]" or "[compelling music starts]".
    3.  **NO TRANSITIONS:** Begin the narration immediately. DO NOT write any introductory or transitional phrases like "In this segment..." or "Now, let's turn our attention to...". The script for this subtopic should stand on its own.
    4.  **FOCUSED CONTENT:** Your entire script must be focused on explaining the event, theme, or figures related to "{sub_topic_title}".
    5.  **EVIDENCE-BASED:** Base your narration *exclusively* on the facts, quotes, and arguments presented in the book text provided below.
    6.  **TARGET LENGTH:** Aim for a narration length of approximately **5 to 9 minutes**. This typically translates to **750-1200 words**, depending on speaking pace. Please ensure the output is a single, self-contained script segment that fits within this timeframe. If you need to prioritize depth over breadth to fit the length, do so.
    7.  **OUTPUT FORMAT:** Start with a markdown heading `## {sub_topic_title}`. Following the heading, write the narration directly in natural, well-formed paragraphs.

    **Full Book Text for Reference:** --- {book_text} ---
    """
    
    try:
        response = model.generate_content(prompt)
        if response and response.text and response.text.strip():
            return response.text.strip()
        else:
            print(f"    - Warning: Received empty or invalid response for script chunk '{sub_topic_title}'.")
            return None
    except Exception as e:
        print(f"    - Error writing script chunk for '{sub_topic_title}': {e}")
        return None

# --- Phase 3: Process and Save ---

def generate_and_save_all_chunks(book_text, book_title, author, outline_data, model):
    """
    Processes each sub-topic individually and saves it as its own substantial chunk file.
    """
    all_final_script_chunks = []
    
    # Add the intro as the first chunk
    formatted_intro = INTRO_TEMPLATE.format(book_title=book_title, author=author).strip()
    all_final_script_chunks.append(formatted_intro)

    # --- ADAPTED LOOP FOR FLEXIBLE STRUCTURE ---
    for main_section in outline_data.get('main_sections', []):
        section_title = main_section.get('title', 'Unknown Section')
        print(f"\n=== PROCESSING SECTION: {section_title} ===")
        
        for subtopic in main_section.get('subtopics', []):
            # Generate one single, self-contained chunk for the subtopic
            chunk = generate_historical_chunk(book_text, book_title, section_title, subtopic, model)
            
            if chunk:
                # --- CHUNK LENGTH MANAGEMENT ---
                # Simple word count check as a proxy for time.
                # Assuming a narration pace of ~150 words per minute for 7-9 minutes.
                words_in_chunk = chunk.split()
                estimated_minutes = len(words_in_chunk) / 150 
                
                if estimated_minutes > 9.5: # A bit of buffer, aiming for <10 min audio
                    print(f"    - WARNING: Generated chunk for '{subtopic}' is estimated to be over 10 minutes ({estimated_minutes:.1f} mins, {len(words_in_chunk)} words).")
                    print("    - NOTE: This script does NOT automatically split chunks. If AI output is consistently too long, manual review or a splitting mechanism would be needed.")
                    # For future implementation: Add logic here to split 'chunk' into smaller parts
                    # if it significantly exceeds the target length.
                
                all_final_script_chunks.append(chunk)
                print(f"✓ Generated script for: {subtopic}")
            else:
                print(f"✗ Failed to generate script for: {subtopic}. Halting.")
                return 0 # Stop if a critical chunk fails
            
            time.sleep(5) # Wait between AI calls for script chunks to avoid rate limiting

    # Ensure the CHUNKS_DIR exists based on config
    os.makedirs(config.CHUNKS_DIR, exist_ok=True)
    print(f"\nSaving {len(all_final_script_chunks)} script chunks to '{config.CHUNKS_DIR}'...")

    # Save each chunk to a file
    for i, chunk_content in enumerate(all_final_script_chunks):
        # Generate filename that aligns with how audio/image generators might find them.
        # Using {i+1:02d} for zero-padded sequential numbering (e.g., 01, 02)
        # This naming is intended to be consistent with how other scripts would find them.
        file_number = str(i + 1).zfill(2) 
        file_path = os.path.join(config.CHUNKS_DIR, f"chunk_{file_number}.txt")
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(chunk_content)
        except Exception as e:
            print(f"Error saving chunk file '{file_path}': {e}")
            continue # Skip saving this file and continue with the next
    
    print(f"\nScript successfully saved as {len(all_final_script_chunks)} substantial chunks.")
    return len(all_final_script_chunks)

# --- MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    # Ensure BOOK_TITLE is correctly formatted for directory creation and display
    # Replace underscores with spaces, and remove common punctuation that might cause issues in paths.
    BOOK_TITLE_PROCESSED = config.BOOK_TITLE.replace("_", " ").replace(":", "").replace(",", "").replace("'", "").replace('"', '')
    AUTHOR = config.AUTHOR # Used in intro template
    
    # Path to the EPUB file
    book_file_path = os.path.join(config.BOOK_DIR, config.BOOK_FILE_NAME)

    if not os.path.exists(book_file_path):
        print(f"Error: The book EPUB file was not found at '{book_file_path}'")
    else:
        api_key = load_api_key()
        if not api_key:
            print("Halting execution: Could not load Google API key.")
        else:
            try:
                # Configure the GenAI client and load the model
                genai.configure(api_key=api_key)
                # Using 'gemini-2.5-flash-lite' as it's generally good for text generation tasks.
                model = genai.GenerativeModel('gemini-2.5-flash-lite') 
                print("✓ Google GenAI client configured and model loaded.")
            except Exception as e:
                print(f"✗ Failed to configure GenAI client or load model: {e}")
                exit() # Exit if AI setup fails

            # --- STEP 1: Get Book Text ---
            full_book_text = get_book_text(book_file_path)
            
            if full_book_text:
                # --- STEP 2: Generate Outline ---
                # FIX: Removed config.AUTHOR from this call as generate_historical_outline only expects 3 args.
                outline_data = generate_historical_outline(full_book_text, BOOK_TITLE_PROCESSED, model)
                
                if outline_data:
                    # --- STEP 3: Save Outline ---
                    # Define outline path relative to config.BOOK_DIR
                    outline_path = os.path.join(config.BOOK_DIR, 'detailed_outline.json')
                    try:
                        with open(outline_path, 'w', encoding='utf-8') as f:
                            json.dump(outline_data, f, indent=2)
                        print(f"Detailed outline saved to: {outline_path}")
                    except Exception as e:
                        print(f"Error saving detailed outline JSON: {e}")
                    
                    # --- STEP 4: Generate and Save Script Chunks ---
                    total_chunks_generated = generate_and_save_all_chunks(
                        full_book_text, 
                        BOOK_TITLE_PROCESSED, 
                        AUTHOR, # AUTHOR is used in INTRO_TEMPLATE, so keep it here for the intro chunk
                        outline_data, 
                        model
                    )
                    
                    if total_chunks_generated > 0: 
                        print(f"\n🎉 SUCCESS! Generated {total_chunks_generated} script chunks.")
                    else:
                        print("\nProcess completed, but script generation failed or produced no chunks.")
                else:
                    print("\nHalting execution: Failed to generate the historical outline.")
            else:
                print("\nHalting execution: Could not retrieve book text from EPUB.")

# --- END OF FILE historical_script_generator.py ---