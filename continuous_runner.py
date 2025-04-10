#!/usr/bin/env python
"""
Continuous Runner for Children's Story Generator

This script runs the story generator in a continuous loop until either:
1. The specified time duration has elapsed
2. The specified number of stories has been generated
3. The GitHub Actions workflow is cancelled

Usage:
    python continuous_runner.py --duration HOURS --count STORIES

Where:
    --duration: Number of hours to run (0 for unlimited)
    --count: Number of stories to generate (0 for unlimited)
"""

import os
import sys
import time
import datetime
import argparse
import logging
import traceback
import json
from pathlib import Path

# Import main generator functions
from main import main as generate_story

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('continuous_runner.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def create_output_directory():
    """Create output directory for storing generated content"""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create subdirectories for stories, images, videos, and logs
    for subdir in ["stories", "videos", "thumbnails", "metadata"]:
        (output_dir / subdir).mkdir(exist_ok=True)
    
    return output_dir

def save_generation_stats(stats):
    """Save generation statistics to a JSON file"""
    stats_file = Path("output/generation_stats.json")
    
    if stats_file.exists():
        # Load existing stats
        with open(stats_file, 'r') as f:
            try:
                existing_stats = json.load(f)
            except json.JSONDecodeError:
                existing_stats = {"generations": []}
    else:
        existing_stats = {"generations": []}
    
    # Add new stats
    existing_stats["generations"].append(stats)
    
    # Save updated stats
    with open(stats_file, 'w') as f:
        json.dump(existing_stats, f, indent=2)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Continuous Story Generator Runner")
    parser.add_argument('--duration', type=float, default=2.34, 
                        help='Duration to run in hours (0 for unlimited, can use fractional hours e.g. 2.5 for 2h30m)')
    parser.add_argument('--count', type=int, default=0, 
                        help='Number of stories to generate (0 for unlimited)')
    return parser.parse_args()

def main():
    """Main function to run the story generator in a loop"""
    args = parse_args()
    
    # Create output directory
    output_dir = create_output_directory()
    
    # Calculate end time if duration is specified
    start_time = datetime.datetime.now()
    if args.duration > 0:
        # Convert hours to hours, minutes, seconds for more precise logging
        hours = int(args.duration)
        minutes = int((args.duration - hours) * 60)
        seconds = int(((args.duration - hours) * 60 - minutes) * 60)
        
        # Calculate exact end time
        end_time = start_time + datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)
        
        logger.info(f"Running for {hours}h {minutes}m {seconds}s until: {end_time}")
    else:
        end_time = None
        logger.info("Running indefinitely (no time limit)")
    
    # Track number of stories generated
    stories_generated = 0
    
    # Loop until conditions are met
    try:
        while True:
            # Check if we've reached the story count limit
            if args.count > 0 and stories_generated >= args.count:
                logger.info(f"Reached target of {args.count} stories. Stopping.")
                break
            
            # Check if we've reached the time limit
            if end_time and datetime.datetime.now() >= end_time:
                logger.info(f"Reached time limit of {args.duration} hours. Stopping.")
                break
            
            # Generate a new story
            logger.info(f"Starting generation #{stories_generated + 1}")
            generation_start = datetime.datetime.now()
            
            try:
                # Create a unique run ID for this generation
                run_id = f"gen_{generation_start.strftime('%Y%m%d_%H%M%S')}"
                
                # Modify environment for this run
                os.environ["STORY_RUN_ID"] = run_id
                os.environ["OUTPUT_DIR"] = str(output_dir)
                
                # Run the main story generator function
                generate_story()
                
                # Track success
                generation_end = datetime.datetime.now()
                generation_time = (generation_end - generation_start).total_seconds()
                
                # Save statistics
                stats = {
                    "run_id": run_id,
                    "start_time": generation_start.isoformat(),
                    "end_time": generation_end.isoformat(),
                    "duration_seconds": generation_time,
                    "status": "success"
                }
                save_generation_stats(stats)
                
                logger.info(f"Generation #{stories_generated + 1} completed in {generation_time:.2f} seconds")
                stories_generated += 1
                
            except Exception as e:
                # Log the error but continue with the next iteration
                logger.error(f"Error during generation: {e}")
                logger.error(traceback.format_exc())
                
                # Save failure statistics
                generation_end = datetime.datetime.now()
                generation_time = (generation_end - generation_start).total_seconds()
                stats = {
                    "run_id": run_id if 'run_id' in locals() else f"failed_{generation_start.strftime('%Y%m%d_%H%M%S')}",
                    "start_time": generation_start.isoformat(),
                    "end_time": generation_end.isoformat(),
                    "duration_seconds": generation_time,
                    "status": "error",
                    "error": str(e)
                }
                save_generation_stats(stats)
            
            # Add a short delay between generations to prevent API rate limiting
            logger.info("Waiting 30 seconds before next generation...")
            time.sleep(30)
            
    except KeyboardInterrupt:
        logger.info("Process interrupted by user. Stopping.")
    
    # Final summary
    logger.info(f"Run completed. Generated {stories_generated} stories.")
    logger.info(f"Total runtime: {(datetime.datetime.now() - start_time).total_seconds()/3600:.2f} hours")

if __name__ == "__main__":
    main()
