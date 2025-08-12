import os
import json
import time
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import google.generativeai as genai
import config

INTRO_TEMPLATE = """
Welcome to Nocturnal Knowledge.

Today, we're exploring "{book_title}" by {author}.

Settle in as we journey through the complete text. If you enjoy this exploration, 
please consider liking this video and subscribing for more deep dives into the world's most influential books.

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
            text = ' '.join(soup.get_text().split())
            full_text.append(text)
        print("Successfully extracted text from EPUB.")
        return "\n\n".join(full_text)
    except Exception as e:
        print(f"An error occurred while parsing the EPUB: {e}")
        return None

def load_api_key():
    """Loads the Google API key from the config file."""
    try:
        with open('../config/api_keys.json', 'r') as f:
            keys = json.load(f)
            return keys['google_api_key']
    except Exception as e:
        print(f"Error loading API key: {e}")
        return None

# --- Phase 1: Generate Detailed Topic Breakdown ---
def generate_detailed_outline(book_text, book_title, model):
    """Creates a comprehensive outline with main topics and detailed subtopics."""
    print("Generating detailed topic breakdown...")
    prompt = f"""
    You are creating a comprehensive outline for a 1-hour audiobook script based on "{book_title}".

    Analyze the full book text and create a structured outline that includes:
    1. Main topic areas
    2. Detailed subtopics under each main area
    3. Specific concepts, principles, and ideas that should be covered

    The output MUST be a JSON object with this structure:
    {{
        "main_topics": [
            {{
                "title": "Main Topic Name",
                "subtopics": [
                    {{
                        "subtitle": "Specific Subtopic",
                        "key_concepts": ["concept1", "concept2", "concept3"],
                        "estimated_duration": "8-10 minutes"
                    }}
                ]
            }}
        ]
    }}

    Guidelines:
    - Aim for 6-8 main topics total
    - Each main topic should have 3-5 detailed subtopics
    - Focus on actionable insights and deep philosophical concepts from the book.

    Here is the full book text:
    --- BOOK TEXT BEGINS ---
    {book_text}
    --- BOOK TEXT ENDS ---
    """
    
    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        outline_data = json.loads(cleaned_response)
        
        print("Successfully generated detailed outline:")
        for i, topic in enumerate(outline_data['main_topics']):
            print(f"  {i+1}. {topic['title']}")
            for j, subtopic in enumerate(topic['subtopics']):
                print(f"     {i+1}.{j+1} {subtopic['subtitle']} ({subtopic['estimated_duration']})")
        
        return outline_data
    except Exception as e:
        print(f"An error occurred during outline generation: {e}")
        return None

# --- Phase 2: Generate Detailed Script for Each Subtopic ---
def generate_detailed_script_chunk(book_text, book_title, subtopic_data, previous_context, model):
    """
    Generates a comprehensive, detailed script for a specific subtopic with natural flow.
    """
    print(f"\nGenerating detailed script for: '{subtopic_data['subtitle']}'...")

    key_concepts_str = ', '.join(subtopic_data['key_concepts'])
    
    prompt = f"""
    You are writing a detailed audiobook narration for "{book_title}".

    **CURRENT SECTION:** {subtopic_data['subtitle']}
    **KEY CONCEPTS TO COVER:** {key_concepts_str}
    **TARGET DURATION:** {subtopic_data['estimated_duration']}
    **PREVIOUS CONTEXT:** {previous_context}

    **YOUR TASK:**
    Create an engaging, flowing narration that follows these critical style requirements:
    1. **CONTINUOUS NARRATION:** Write as a single, continuous story. Start by smoothly transitioning from the previous context.
    2. **DEEP EXPLORATION:** Thoroughly explore each key concept with clear explanations, using direct quotes, examples, and analogies from the book.
    3. **NO META-COMMENTARY:** Do NOT use phrases like "Welcome back," "In this segment," or "In the next part." The narration should be seamless.
    4. **TONE:** Write like a thoughtful narrator exploring the book's ideas in depth, as if having an intimate conversation with the listener.
    5. **FORMAT:** Start with the markdown heading `## {subtopic_data['subtitle']}` and then write the narration in natural, spoken-word paragraphs.

    **BOOK TEXT FOR REFERENCE:**
    ---
    {book_text}
    ---
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"An error occurred during script generation for '{subtopic_data['subtitle']}': {e}")
        return None

# --- Phase 3: Process All Topics and Subtopics ---
def generate_all_script_chunks(book_text, book_title, outline_data, model):
    """Process all main topics and their subtopics to generate script chunks."""
    all_chunks = []
    
    # Correctly initialize the context to be generic and book-specific
    previous_context = f"We are beginning our journey into the core ideas of the book, '{book_title}'."
    
    for main_topic in outline_data['main_topics']:
        print(f"\n=== PROCESSING MAIN TOPIC: {main_topic['title']} ===")
        
        for subtopic in main_topic['subtopics']:
            chunk = generate_detailed_script_chunk(book_text, book_title, subtopic, previous_context, model)
            if chunk:
                all_chunks.append(chunk)
                print(f"✓ Generated script for: {subtopic['subtitle']}")
                
                # Update context for the next chunk
                previous_context = f"Having just explored the concepts within '{subtopic['subtitle']}', we now transition to the next idea."
            else:
                print(f"✗ Failed to generate script for: {subtopic['subtitle']}")
                return None  # Stop if any chunk fails
            
            time.sleep(3)  # API rate limiting
    
    return all_chunks

# --- Phase 4: Save Chunks ---
def save_chunks_to_files(script_chunks, book_title, author):
    """Save script chunks to individual files."""
    # Uses the CHUNKS_DIR from our config file
    os.makedirs(config.CHUNKS_DIR, exist_ok=True)

    # Format and add intro
    formatted_intro = INTRO_TEMPLATE.format(book_title=book_title.replace("_", " "), author=author).strip()
    final_chunks = [formatted_intro] + script_chunks
    
    # Save each chunk
    for i, chunk_content in enumerate(final_chunks):
        file_path = os.path.join(config.CHUNKS_DIR, f"chunk_{str(i+1).zfill(2)}.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(chunk_content)
    
    print(f"\nScript successfully saved as {len(final_chunks)} detailed chunks in: {config.CHUNKS_DIR}")
    return len(final_chunks)

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
            model = genai.GenerativeModel('gemini-2.0-flash') 
            
            full_book_text = get_book_text(book_file_path) # Simplified from previous code
            if full_book_text:
                # Generate detailed outline
                outline_data = generate_detailed_outline(full_book_text, BOOK_TITLE.replace("_", " "), model)
                
                if outline_data:
                    # Save outline for reference
                    outline_path = os.path.join(config.BOOK_DIR, 'detailed_outline.json')
                    os.makedirs(os.path.dirname(outline_path), exist_ok=True)
                    with open(outline_path, 'w', encoding='utf-8') as f:
                        json.dump(outline_data, f, indent=2)
                    print(f"Detailed outline saved to: {outline_path}")
                    
                    # Generate all script chunks
                    all_script_chunks = generate_all_script_chunks(full_book_text, BOOK_TITLE.replace("_", " "), outline_data, model)
                    
                    if all_script_chunks:
                        total_chunks = save_chunks_to_files(all_script_chunks, BOOK_TITLE, AUTHOR)
                        print(f"\n🎉 SUCCESS! Generated {total_chunks} detailed script chunks.")
                    else:
                        print("❌ Failed to generate all script chunks.")
                else:
                    print("❌ Failed to generate detailed outline.")
            else:
                print("❌ Failed to extract text from EPUB.")