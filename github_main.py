#!/usr/bin/env python
"""
GitHub Actions Main Runner for Children's Story Generator

This version of the main script is specifically designed to work with GitHub Actions and the continuous runner.
It redirects outputs to appropriate directories and handles environment variables set by the workflow.
"""

import os
import sys
import base64
import datetime
import tempfile
import json
import shutil
from pathlib import Path

# Import from our modules
from config.settings import safety_settings
from utils.drive_utils import test_google_drive_api, download_file_from_google_drive, upload_text_file_to_drive
from generators.prompt_generator import generate_prompt
from generators.story_generator import retry_story_generation, generate
from generators.audio_generator import generate_audio
from generators.video_generator import generate_video
from metadata.seo_generator import generate_seo_metadata, default_seo_metadata, generate_thumbnail

def main():
    """GitHub Actions optimized main function that orchestrates the entire process"""
    print("--- Starting CI/CD Story Generator ---")
    
    # Get run ID and output directory from environment
    run_id = os.environ.get("STORY_RUN_ID", datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    output_base_dir = os.environ.get("OUTPUT_DIR", "output")
    output_dir = Path(output_base_dir)
    
    # Ensure output directories exist
    stories_dir = output_dir / "stories"
    videos_dir = output_dir / "videos"
    thumbnails_dir = output_dir / "thumbnails"
    metadata_dir = output_dir / "metadata"
    
    for directory in [stories_dir, videos_dir, thumbnails_dir, metadata_dir]:
        directory.mkdir(exist_ok=True)
    
    # Log file for this run
    log_file = output_dir / f"{run_id}.log"
    
    # Redirect stdout to both console and log file
    class Logger:
        def __init__(self, filename):
            self.terminal = sys.stdout
            self.log = open(filename, "w")
        
        def write(self, message):
            self.terminal.write(message)
            self.log.write(message)
            self.flush()
            
        def flush(self):
            self.terminal.flush()
            self.log.flush()
    
    sys.stdout = Logger(log_file)
    
    # Generate the story using the retry mechanism
    print(f"Run ID: {run_id}")
    print(f"Output directory: {output_dir}")
    
    result = retry_story_generation(use_prompt_generator=True)
    
    # Check if we have all required outputs
    if not result or not result.get("story_text") or not result.get("image_files"):
        print("⚠️ Story generation failed or incomplete")
        return False
    
    # Save the story text
    story_text = result["story_text"]
    image_files = result["image_files"]
    temp_dir = result.get("temp_dir") or tempfile.mkdtemp()
    prompt_text = result.get("prompt_text", "")
    
    # Save story to file
    story_file = stories_dir / f"{run_id}_story.txt"
    with open(story_file, "w", encoding="utf-8") as f:
        f.write(story_text)
    print(f"✅ Story saved to {story_file}")
    
    # Generate audio for the story
    audio_results = generate_audio(story_text, temp_dir)
    if not audio_results:
        print("⚠️ Audio generation failed")
        return False
    
    # Copy image files to output directory
    image_output_dir = output_dir / "stories" / f"{run_id}_images"
    image_output_dir.mkdir(exist_ok=True)
    
    for i, img_path in enumerate(image_files):
        if os.path.exists(img_path):
            dest_path = image_output_dir / f"image_{i:02d}.png"
            shutil.copy2(img_path, dest_path)
    
    # Generate video from images and audio
    video_results = generate_video(story_text, image_files, audio_results, temp_dir)
    if not video_results:
        print("⚠️ Video generation failed")
        return False
    
    # Generate SEO metadata
    metadata = generate_seo_metadata(story_text, image_files, prompt_text)
    
    # Save metadata to file
    metadata_file = metadata_dir / f"{run_id}_metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    # Generate thumbnail
    thumbnail_path = generate_thumbnail(image_files, story_text, metadata)
    
    # Save output video
    output_path = video_results.get("output_path")
    if output_path and os.path.exists(output_path):
        video_output_path = videos_dir / f"{run_id}_video.mp4"
        shutil.copy2(output_path, video_output_path)
        print(f"✅ Video saved to {video_output_path}")
    
    # Save thumbnail
    if thumbnail_path and os.path.exists(thumbnail_path):
        thumbnail_output_path = thumbnails_dir / f"{run_id}_thumbnail.jpg"
        shutil.copy2(thumbnail_path, thumbnail_output_path)
        print(f"✅ Thumbnail saved to {thumbnail_output_path}")
    
    # No need to try Google Drive upload in GitHub Actions
    print("✅ Generation completed successfully")
    return True

if __name__ == "__main__":
    success = main()
    # Return exit code based on success (used by continuous_runner.py)
    sys.exit(0 if success else 1)
