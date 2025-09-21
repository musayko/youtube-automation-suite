# src/storyteller.py (New "Immersive Storyteller" with Smart Intro)

import os
import json
import time
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import google.generativeai as genai
import config

# --- HELPER FUNCTIONS (No change needed) ---
def get_book_text(epub_path):
    print(f"Reading and parsing EPUB file from: {epub_path}")
    # ... (code is correct and unchanged)
    try:
        book = epub.read_epub(epub_path)
        full_text = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text = ' '.join(soup.get_text().split())
            full_text.append(text)
        print("Successfully extracted text from EPUB.")
        return "\n\n".join(full_text)
    except Exception as e:
        print(f"An error occurred while parsing the EPUB: {e}")
        return None

def load_api_key():
    # ... (code is correct and unchanged)
    try:
        with open('../config/api_keys.json', 'r') as f:
            keys = json.load(f)
            return keys['google_api_key']
    except Exception as e:
        print(f"Error loading API key: {e}")
        return None

# --- NEW SMART INTRO GENERATION ---
def generate_intro_hook(book_text, book_title, author, model):
    """Asks the AI to generate a single, compelling hook sentence for the book's intro."""
    print("Phase 1: Generating a unique intro hook...")
    prompt = f"""
    You are a scriptwriter for a captivating history documentary series.
    Based on the full text of the book "{book_title}" by {author}, find the single most surprising, strange, or fascinating fact, story, or "what if" question.

    **Your Task:**
    Create a short, intriguing hook (1-2 sentences) that would make someone immediately want to hear more.
    Start with a phrase like "Did you know..." or "What if...".

    **Example Hook:**
    "Did you know that in Dark Age Britain, breakfast was considered a philosophical concept, and often consisted of boiled moss and regret?"

    **Output ONLY the hook itself.**

    Full book text for analysis is below. Find the most interesting nugget of information.
    ---
    {book_text}
    ---
    """
    try:
        response = model.generate_content(prompt)
        hook = response.text.strip().replace('"', '')
        print(f"  > Generated Hook: {hook}")
        return hook
    except Exception as e:
        print(f"  > An error occurred during intro hook generation: {e}")
        # Provide a safe fallback if the API fails
        return f"Tonight, we uncover the hidden truths within '{book_title}'."

# --- IMMERSIVE SCRIPT GENERATION ---
def generate_narrative_arc_outline(book_text, book_title, author, model):
    """Creates a narrative arc of compelling scene titles."""
    print("Phase 2: Generating a Narrative Arc...")
    # ... (This function is the same as the previous version, no changes needed)
    prompt = f"""
    You are a master storyteller and screenwriter, adapting the book "{book_title}" by {author} into an immersive, 
    podcast experience. Your task is to create a narrative arc by identifying 10-15 key "scenes" or "vignettes" 
    from the book. Do not create a simple table of contents. Instead, think about the most vivid stories, analogies, 
    and powerful concepts. Give each scene a compelling, evocative title. 
    The output MUST be a JSON array of strings, where each string is a scene title. 
    Example for a history book: 
    ["Waking Up in a Mud Hut", "The Philosophy of Breakfast", "A Conversation with the Village Elder", "The Shadow of the Vikings"] 
    Full book text for analysis is below. Find the most powerful moments and turn them into scenes.
    ---
    {book_text}
    ---
    """
    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        outline = json.loads(cleaned_response)
        print("Successfully generated Narrative Arc:")
        for i, title in enumerate(outline):
            print(f"  - Scene {i+1}: {title}")
        return outline
    except Exception as e:
        print(f"An error occurred during narrative arc generation: {e}")
        return None

def generate_immersive_script_chunk(book_text, book_title, scene_title, model):
    """Writes a script chunk in the immersive, second-person, sensory style."""
    print(f"  > Phase 3: Writing immersive script for scene: '{scene_title}'...")
    # ... (This function is the same as the previous version, no changes needed)
    prompt = f"""
    You are a master storyteller, captivating historical narrator. 
    Your task is to write the script for a single scene titled "{scene_title}" based on the book "{book_title}". 
    **CRITICAL STYLE REQUIREMENTS:
    ** 1. **POINT OF VIEW:** Write in the second person ("You are...", "You feel..."). 
    2. **SENSORY LANGUAGE:** Use rich, visceral, sensory language (sights, sounds, smells). 
    3. **TONE:** Intimate, conversational, and slightly witty. 
    4. **CONTENT:** Transform the key concepts related to "{scene_title}" into an immersive scene. 
    5. **NO META-COMMENTARY:** No "Welcome back" or "In this part...". 
    6. **EXAMPLE:** "You wake up with a sneeze and a goat staring directly into your soul. Your bed is straw. Literally straw." 
    **OUTPUT FORMAT:** Start with a markdown heading `## {scene_title}`. 
    Write the narration directly. Full book text is below for reference.
    ---
    {book_text}
    ---
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"    - Error writing script chunk: {e}")
        return None

def save_chunks_to_files(script_chunks, book_title):
    """Saves the final list of script chunks to numbered files."""
    os.makedirs(config.CHUNKS_DIR, exist_ok=True)
    for i, chunk_content in enumerate(script_chunks):
        file_path = os.path.join(config.CHUNKS_DIR, f"chunk_{str(i+1).zfill(2)}.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(chunk_content)
    print(f"\nImmersive script successfully saved into {len(script_chunks)} chunk files in: {config.CHUNKS_DIR}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # Pull settings from the central config file
    BOOK_TITLE = config.BOOK_TITLE
    AUTHOR = config.AUTHOR
    BOOK_FILE_NAME = config.BOOK_FILE_NAME
    
    book_file_path = os.path.join(config.BOOK_DIR, BOOK_FILE_NAME)

    if not os.path.exists(book_file_path):
        print(f"Error: The file was not found at {book_file_path}")
    else:
        api_key = load_api_key()
        if not api_key:
            print("Could not load API key. Exiting.")
        else:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash') # Using a capable model
            
            full_book_text = get_book_text(book_file_path)
            
            if full_book_text:
                # 1. Generate the smart hook
                hook_sentence = generate_intro_hook(full_book_text, BOOK_TITLE.replace("_", " "), AUTHOR, model)
                
                # 2. Build the final intro using the hook
                final_intro_text = f""" Welcome to Nocturnal Knowledge

today we begin with the world of "{BOOK_TITLE.replace("_", " ")}".

{hook_sentence}

But before we begin, if you enjoy these explorations, don’t forget to like the video and subscribe. Drop a comment too—let me know where you’re tuning in from, because this journey isn’t just mine, it’s ours.

Now, dim the lights, clear your mind, and let’s begin today’s voyage together.
"""
                # 3. Generate the narrative arc for the rest of the content
                narrative_arc = generate_narrative_arc_outline(full_book_text, BOOK_TITLE.replace("_", " "), AUTHOR, model)

                if narrative_arc:
                    all_chunks = [final_intro_text] # Start our list with the completed intro
                    
                    # 4. Generate an immersive script for each scene
                    for scene in narrative_arc:
                        chunk = generate_immersive_script_chunk(full_book_text, BOOK_TITLE.replace("_", " "), scene, model)
                        if chunk:
                            all_chunks.append(chunk)
                        time.sleep(5)
                    
                    # 5. Save all the final chunks
                    save_chunks_to_files(all_chunks, BOOK_TITLE)
                    print("\n--- Immersive script generation process complete! ---")