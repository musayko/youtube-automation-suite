import os
import subprocess
import glob
import random
from natsort import natsorted
import config  # Use our new central config file

# All hardcoded paths have been removed. They are now accessed via the 'config' module.

def get_audio_duration(audio_file_path):
    """Gets the duration of an audio file in seconds using ffprobe."""
    command = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', audio_file_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return float(result.stdout)
    except Exception as e:
        print(f"[ERROR] Could not get duration for {os.path.basename(audio_file_path)}: {e}")
        return None

def create_placeholder_image(width=1920, height=1080, text=""):
    """Creates a simple placeholder image if no images are available for a part."""
    from PIL import Image, ImageDraw, ImageFont
    
    img = Image.new('RGB', (width, height), color='#1a1a1a')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except:
        font = ImageFont.load_default()
    
    # Use the book title from the config file, replacing underscores with spaces
    display_text = text if text else config.BOOK_TITLE.replace("_", " ")
    bbox = draw.textbbox((0, 0), display_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    position = ((width - text_width) // 2, (height - text_height) // 2)
    draw.text(position, display_text, fill='white', font=font)
    
    return img

def create_animated_slideshow(images, total_duration, output_path, part_number):
    """
    Creates a smooth, full-duration animated slideshow by prescaling images
    and using duration-aware animation logic.
    """
    print(f"Step 1/2: Creating animated slideshow for part {part_number}...")

    if not images:
        print(f"[WARNING] No images found for part {part_number}. Creating placeholder...")
        temp_placeholder = os.path.join(config.TEMP_DIR, f"placeholder_{part_number}.png")
        create_placeholder_image(text=f"Part {part_number}").save(temp_placeholder)
        images = [temp_placeholder]

    image_duration = total_duration / len(images)
    if image_duration <= 2:
        print("[WARNING] Image duration is very short. Animations might be fast.")
    
    duration_in_frames = int(image_duration * 24)
    if duration_in_frames <= 0:
        print(f"[ERROR] Cannot create animation with zero or negative duration for part {part_number}.")
        return False

    base_filter_chain = "scale=w='if(gt(a,16/9),-1,1920)':h='if(gt(a,16/9),1080,-1)',crop=1920:1080,scale=8000:-1"
    
    animation_presets = {
        'smooth_zoom_in':  f"zoompan=z='lerp(1,1.1,on/{duration_in_frames})':d={duration_in_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=24",
        'smooth_zoom_out': f"zoompan=z='lerp(1.1,1,on/{duration_in_frames})':d={duration_in_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=24",
        'pan_right':       f"zoompan=z=1.1:d={duration_in_frames}:x='(iw-iw/zoom)*on/{duration_in_frames}':y='(ih-ih/zoom)/2':s=1920x1080:fps=24",
        'pan_left':        f"zoompan=z=1.1:d={duration_in_frames}:x='(iw-iw/zoom)*(1-on/{duration_in_frames})':y='(ih-ih/zoom)/2':s=1920x1080:fps=24",
    }
    preset_keys = list(animation_presets.keys())
    
    temp_clips = []
    for i, image_path in enumerate(images):
        temp_clip_path = os.path.join(config.TEMP_DIR, f"temp_clip_{part_number}_{i}.mp4")
        
        if not os.path.exists(image_path):
            print(f"[WARNING] Image not found, skipping: {image_path}")
            continue
            
        temp_clips.append(temp_clip_path)
        
        effect_key = preset_keys[i % len(preset_keys)]
        animation_filter = animation_presets[effect_key]

        print(f"  > Animating image {i+1}/{len(images)} with '{effect_key}' effect...")
        
        cmd = [
            'ffmpeg', '-y', '-loop', '1', '-i', image_path,
            '-vf', f"{base_filter_chain},{animation_filter}",
            '-c:v', 'libx264', '-t', str(image_duration), '-pix_fmt', 'yuv420p',
            temp_clip_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[ERROR] FFmpeg failed for image {i+1}:\n{result.stderr}")
            if temp_clip_path in temp_clips: temp_clips.remove(temp_clip_path)

    existing_clips = [clip for clip in temp_clips if os.path.exists(clip)]
    if not existing_clips:
        print("[ERROR] No video clips were created successfully for this part.")
        return False

    print(f"  > Stitching {len(existing_clips)} animated clips together...")
    concat_list_path = os.path.join(config.TEMP_DIR, f'animated_clips_{part_number}.txt')
    with open(concat_list_path, 'w') as f:
        for clip_path in existing_clips:
            f.write(f"file '{os.path.abspath(clip_path)}'\n")

    cmd_concat = [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_list_path,
        '-c', 'copy', output_path
    ]
    result = subprocess.run(cmd_concat, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] FFmpeg concatenation failed:\n{result.stderr}")
        return False
        
    for clip in existing_clips: os.remove(clip)
    os.remove(concat_list_path)

    return True

def process_all_parts():
    """Fully dynamic processing that automatically adapts to any number of audio files."""
    temp_dir = os.path.join(config.VIDEO_DIR, 'temp_files')
    os.makedirs(temp_dir, exist_ok=True)
    
    audio_files = natsorted(glob.glob(os.path.join(config.AUDIO_DIR, 'audio_part_*.wav')))
    overlay_files = glob.glob(os.path.join(config.OVERLAYS_DIR, '*.*'))

    if not audio_files:
        print(f"Error: No audio files found in {config.AUDIO_DIR}")
        print("Please run the audio generator first.")
        return False

    print(f"🎵 Found {len(audio_files)} audio files to process.")
    print(f"📁 Book: {config.BOOK_TITLE}")
    print(f"🎬 Creating video with {len(audio_files)} segments...")
    
    successful_parts = 0

    for i, audio_path in enumerate(audio_files):
        part_num_str = os.path.basename(audio_path).replace('audio_part_', '').replace('.wav', '')
        print(f"\n--- Processing Part {part_num_str}/{len(audio_files)} ---")

        images = natsorted(glob.glob(os.path.join(config.IMAGES_DIR, f'image_part_{part_num_str}_img_*.png')))
        if not images:
            print(f"Warning: No images found for part {part_num_str}. Will create placeholder.")
        else:
            print(f"Found {len(images)} images for part {part_num_str}.")
        
        duration = get_audio_duration(audio_path)
        if not duration:
            print(f"Skipping part {part_num_str} due to audio duration error.")
            continue
        
        print(f"Audio duration: {duration:.2f} seconds")
        
        slideshow_path = os.path.join(temp_dir, f'slideshow_{part_num_str}.mp4')
        if not create_animated_slideshow(images, duration, slideshow_path, part_num_str):
            print(f"Failed to create slideshow for part {part_num_str}. Skipping.")
            continue

        processed_segment_path = os.path.join(temp_dir, f'processed_segment_{part_num_str}.mp4')
        overlay_path = random.choice(overlay_files) if overlay_files else None
        
        overlay_name = os.path.basename(overlay_path) if overlay_path else 'None'
        print(f"Step 2/2: Adding audio and overlay ('{overlay_name}') to part {part_num_str}...")

        if overlay_path:
            filter_complex_str = "[1:v]colorkey=black:0.3:0.2[ckout];[0:v][ckout]overlay[v]"
            ffmpeg_overlay_cmd = [
                'ffmpeg', '-y', '-i', slideshow_path, '-stream_loop', '-1', '-i', overlay_path, '-i', audio_path,
                '-filter_complex', filter_complex_str, '-map', '[v]', '-map', '2:a',
                '-c:v', 'libx264', '-c:a', 'aac', '-b:a', '192k', '-shortest', processed_segment_path
            ]
        else:
            ffmpeg_overlay_cmd = [
                'ffmpeg', '-y', '-i', slideshow_path, '-i', audio_path,
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', processed_segment_path
            ]
        
        result = subprocess.run(ffmpeg_overlay_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[ERROR] FFmpeg failed for part {part_num_str}:\n{result.stderr}")
            continue
        
        successful_parts += 1
        print(f"-> Part {part_num_str} complete! ({successful_parts}/{len(audio_files)} total)")
        
    print(f"\n--- Processing Summary ---")
    print(f"Successfully processed: {successful_parts}/{len(audio_files)} parts")
    return successful_parts > 0

def concatenate_final_video():
    """Stitches all processed segments into the final video."""
    print("\n--- Assembling Final Video ---")
    temp_dir = os.path.join(config.VIDEO_DIR, 'temp_files')
    processed_segments = natsorted(glob.glob(os.path.join(temp_dir, 'processed_segment_*.mp4')))
    
    if not processed_segments:
        print("No processed segments to assemble. Halting.")
        return None

    print(f"Found {len(processed_segments)} segments to concatenate.")
    
    concat_list_path = os.path.join(temp_dir, 'final_concat_list.txt')
    with open(concat_list_path, 'w') as f:
        for seg in processed_segments:
            f.write(f"file '{os.path.abspath(seg)}'\n")
            
    final_video_path = os.path.join(config.VIDEO_DIR, f"{config.BOOK_TITLE}_final_video.mp4")
    os.makedirs(config.VIDEO_DIR, exist_ok=True)
    
    ffmpeg_concat_cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_list_path, '-c', 'copy', final_video_path]
    
    result = subprocess.run(ffmpeg_concat_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] FFmpeg failed during final concatenation:\n{result.stderr}")
        return None
    
    print(f"Success! Final video saved to: {final_video_path}")
    return final_video_path

def add_narration_and_music(video_with_narration_path):
    """Adds background music to the final video, looping it if necessary."""
    print("\n--- Final Step: Adding Background Music ---")
    
    music_files = glob.glob(os.path.join(config.MUSIC_DIR, '*.*'))
    if not music_files:
        print("No background music found. Final video will only have narration.")
        final_video_path = os.path.join(config.VIDEO_DIR, f"{config.BOOK_TITLE}_final_video_with_music.mp4")
        try:
            os.rename(video_with_narration_path, final_video_path)
        except OSError as e:
            print(f"[ERROR] Could not rename final file: {e}")
        return
    
    music_path = random.choice(music_files)
    final_video_path = os.path.join(config.VIDEO_DIR, f"{config.BOOK_TITLE}_final_video_with_music.mp4")
    
    print(f"Mixing narration with background music: '{os.path.basename(music_path)}'")
    
    filter_complex_str = (
        "[0:a]pan=stereo|c0=c0|c1=c0[narration_centered];"
        "[1:a]volume=0.15[music_bg];"
        "[narration_centered][music_bg]amix=inputs=2:duration=first[final_audio]"
    )

    cmd_mix_audio = [
        'ffmpeg', '-y', '-i', video_with_narration_path, '-stream_loop', '-1', '-i', music_path,
        '-filter_complex', filter_complex_str, '-map', '0:v', '-map', '[final_audio]',
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', final_video_path
    ]
    
    print("Executing FFmpeg command to mix audio...")
    result = subprocess.run(cmd_mix_audio, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] FFmpeg failed while mixing audio:\n{result.stderr}")
        return

    print(f"Success! Final video with music and narration saved to: {final_video_path}")


if __name__ == "__main__":
    print(f"=== Video Assembly for '{config.BOOK_TITLE}' ===")
    
    if process_all_parts():
        video_with_narration = concatenate_final_video()
        if video_with_narration:
            add_narration_and_music(video_with_narration)
    else:
        print("\nVideo assembly failed. No parts were processed successfully. Please check the errors above.")