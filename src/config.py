import os

# --- THIS IS THE ONLY FILE YOU NEED TO EDIT FOR A NEW BOOK ---
BOOK_TITLE = "Tthink faster talk smarter"
AUTHOR = "Matt Abrahams"
# The name of the .epub or .pdf file inside the book's folder
BOOK_FILE_NAME = "Think_Faster_Talk_Smarter.epub"
# -------------------------------------------------------------

# --- Project Directories (No changes needed below) ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BOOK_DIR = os.path.join(BASE_DIR, 'books', BOOK_TITLE)
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
MUSIC_DIR = os.path.join(BASE_DIR, 'music')
OVERLAYS_DIR = os.path.join(BASE_DIR, 'overlays')

# --- Book-Specific Directories ---
CHUNKS_DIR = os.path.join(BOOK_DIR, 'chunks') # Our new "source of truth"
AUDIO_DIR = os.path.join(BOOK_DIR, 'audio')
IMAGES_DIR = os.path.join(BOOK_DIR, 'images')
VIDEO_DIR = os.path.join(BOOK_DIR, 'video')
TEMP_DIR = os.path.join(VIDEO_DIR, 'temp_files')