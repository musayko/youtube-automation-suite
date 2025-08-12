# main.py
import src.master_script_generator as script_gen
import src.audio_generator_gemini as audio_gen
import src.image_generator as image_gen
import src.video_assembler as video_assembler

def run_ffmpeg_pipeline():
    print("--- STARTING FFMPEG PIPELINE ---")
    # script_gen.main()
    # audio_gen.main()
    # image_gen.main()
    # video_assembler.main()
    print("--- FFMPEG PIPELINE COMPLETE ---")

if __name__ == "__main__":
    run_ffmpeg_pipeline()