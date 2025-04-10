# generators/story_generator.py
import os
import re
import json
import tempfile
import time
import threading
import traceback
import google.generativeai as genai
# Import display functions - handle both IPython and non-IPython environments
try:
    from IPython import get_ipython
    from IPython.display import display, Image as IPythonImage
    # Check if we're in IPython/Jupyter environment
    in_notebook = get_ipython() is not None
except ImportError:
    in_notebook = False
    
from PIL import Image as PILImage
import io
import base64

from utils.api_utils import retry_api_call
from utils.media_utils import collect_complete_story
from generators.prompt_generator import generate_prompt
from config.settings import safety_settings

def retry_story_generation(use_prompt_generator=True, prompt_input="Create a unique children's story with a different animal character, setting, and adventure theme."):
    """
    Persistently retries story generation when image loading fails or JSON errors occur.
    This function will keep retrying every 7 seconds until all conditions are met:
    1. No JSON errors in stream processing
    2. Images are properly loaded
    3. At least 6 story segments are generated
    
    Args:
        use_prompt_generator: Whether to use the prompt generator
        prompt_input: The prompt input to guide story generation
        
    Returns:
        The result of the successful generation
    """
    import time
    import threading
    
    # Set initial state
    success = False
    max_retries = 1000  # Set a reasonable limit
    retry_count = 0
    retry_delay = 7  # Run every 7 seconds as specified
    
    # Create a container for results
    results = {"story_text": None, "image_files": [], "output_path": None, "thumbnail_path": None, "metadata": None}
    
    # Create a global temp directory for flag files
    import tempfile
    import os
    temp_dir = tempfile.mkdtemp()
    
    def check_generation_status():
        # This helper function checks if the generation was successful
        # Based on the presence of images and sufficient story segments
        nonlocal success
        
        if not results["story_text"] or not results["image_files"]:
            return False
        
        # Check if we have at least 6 story segments
        try:
            story_segments = collect_complete_story(results["story_text"], return_segments=True)
            if len(story_segments) < 6:
                print(f"⚠️ Insufficient story segments: {len(story_segments)} (need at least 6)")
                return False
                
            # Check if we have sufficient images
            if len(results["image_files"]) < 6:
                print(f"⚠️ Insufficient images: {len(results['image_files'])} (need at least 6)")
                return False
            
            # We don't need to check for output_path anymore - we're only validating story and images here
            # If we have enough story segments and images, mark as successful
            # The audio/video generation will happen in main.py after this function returns
            
            # If we get here, story and image generation was successful
            success = True
            return True
        except Exception as e:
            print(f"⚠️ Error checking generation status: {e}")
            return False
    
    # Define a wrapper function that will capture the results
    def generation_wrapper():
        nonlocal results
        try:
            # Create a clean temporary directory for each attempt
            import tempfile
            import os
            temp_dir = tempfile.mkdtemp()
            
            # Call the main generate function
            print(f"\n🔄 Retry attempt #{retry_count+1} for story generation...")
            print(f"⏳ Starting generation with prompt: {prompt_input[:50]}...")
            
            # This is a wrapper that will call the actual generate function
            # but will capture its outputs for our status checks
            result = generate(use_prompt_generator=use_prompt_generator, prompt_input=prompt_input)
            
            # Directly use the returned dictionary from generate
            if result and isinstance(result, dict):
                # Update our results with what came back from generate
                if 'story_text' in result and result['story_text']:
                    results["story_text"] = result['story_text']
                if 'image_files' in result and result['image_files']:
                    results["image_files"] = result['image_files']
                if 'temp_dir' in result and result['temp_dir']:
                    results["temp_dir"] = result['temp_dir']
                if 'prompt_text' in result and result['prompt_text']:
                    results["prompt_text"] = result['prompt_text']
                
            # Check if generation was successful
            check_generation_status()
        except Exception as e:
            print(f"⚠️ Error in generation attempt: {e}")
            import traceback
            traceback.print_exc()
    
    # Main retry loop
    while not success and retry_count < max_retries:
        retry_count += 1
        
        # Start generation in current thread (blocking)
        generation_wrapper()
        
        # If successful, break the loop
        if success:
            print(f"✅ Story generation successful after {retry_count} attempts!")
            break
            
        # If not successful, wait and retry
        print(f"⚠️ Generation attempt #{retry_count} failed or incomplete.")
        print(f"🔄 Retrying in {retry_delay} seconds...")
        time.sleep(retry_delay)
    
    if not success:
        print(f"⚠️ Maximum retry attempts ({max_retries}) reached without success.")
    
    # Return the results regardless of success state
    # This allows partial results to be used if available
    return results

def generate(use_prompt_generator=True, prompt_input="Create a unique children's story with a different animal character, setting, and adventure theme."):
    """
    Generates a story using the Gemini model.

    Args:
        use_prompt_generator: Whether to use the prompt generator
        prompt_input: The prompt input to guide story generation if prompt_generator is False

    Returns:
        Dict containing story text, segments, image data, and other information
    """
    # Initialize the Gemini client
    try:
        # Configure the API client with the API key
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        print("✅ Initialized genai with API key")
    except Exception as e:
        print(f"🔴 Error initializing genai configuration: {e}")
        return None

    # Set model to use (using the image-enabled model)
    model_name = "gemini-2.0-flash-exp-image-generation"

    # Create a generative model instance
    try:
        model = genai.GenerativeModel(model_name)
        print(f"✅ Created generative model: {model_name}")
    except Exception as e:
        print(f"🔴 Error creating generative model: {e}")
        return None

    # --- Modified Prompt for Reliable Image Generation ---
    # If using prompt generator, get a specially formatted prompt
    # Else, use the provided prompt_input directly with formatting
    if use_prompt_generator:
        prompt_result = retry_api_call(generate_prompt, prompt_input=prompt_input)
        if prompt_result:
            prompt_text = prompt_result
            print(f"📝 Using generated prompt: {prompt_text}")
        else:
            print("⚠️ Prompt generation failed, using fallback prompt")
            prompt_text = f"Generate a story about a clever fox going on an adventure in an enchanted forest in a highly detailed 3d cartoon animation style. For each scene, generate a high-quality, photorealistic image for each scene **in landscape orientation suitable for a widescreen (16:9 aspect ratio) YouTube video**. Ensure maximum detail, vibrant colors, and professional lighting."
    else:
        # Use the provided prompt_input directly
        prompt_text = prompt_input
        print(f"📝 Using direct prompt: {prompt_text}")
    # --- End Modified Prompt ---

    contents = [{
        "role": "user",
        "parts": [
            {"text": prompt_text}
        ]
    }]
    
    generate_params = {
        "generation_config": {
            "response_mime_types": ["image/jpeg", "text/plain"],
        },
        "safety_settings": safety_settings,
    }

    # Track image load failures
    image_load_failures = 0
    max_image_retries = 3

    print(f"ℹ️ Using Story Generation Model: {model_name}")
    print("⏳ Generating story with images (this may take a few minutes)...")

    try:
        # Attempt streaming API first for better user experience
        try:
            print("--- Using Streaming API for story generation ---")
            
            # Generate content using the stream method
            stream = model.generate_content(
                contents,
                stream=True,
                **generate_params
            )

            # Process the streaming response
            story_text = ""
            story_segments = []
            current_segment = ""
            image_data = []

            for chunk in stream:
                try:
                    # Process text
                    if hasattr(chunk, 'text') and chunk.text:
                        print(chunk.text, end='')
                        story_text += chunk.text
                        current_segment += chunk.text

                        # When we get an obvious break in the story, split into a new segment
                        if re.search(r'\n\s*\n', current_segment):
                            parts = re.split(r'\n\s*\n', current_segment, 1)
                            
                            if len(parts) > 1:
                                story_segments.append(parts[0])
                                current_segment = parts[1]
                            else:
                                story_segments.append(current_segment)
                                current_segment = ""

                    # Process images when they arrive
                    if hasattr(chunk, 'parts'):
                        for part in chunk.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                try:
                                    # Display image if in notebook
                                    if in_notebook:
                                        display(IPythonImage(
                                            data=base64.b64decode(part.inline_data.data),
                                            format=part.inline_data.mime_type.split('/')[-1]
                                        ))
                                    
                                    # Save image data for later use
                                    image_data.append({
                                        'data': part.inline_data.data,
                                        'mime_type': part.inline_data.mime_type
                                    })
                                except Exception as img_err:
                                    print(f"\n⚠️ Error processing image: {img_err}")
                                    image_load_failures += 1
                except json.JSONDecodeError as json_err:
                    print(f"\n⚠️ JSON error in stream processing: {json_err}")
                    return None  # Signal that we need to retry with JSONDecodeError
                except Exception as chunk_err:
                    print(f"\n⚠️ Error processing chunk: {chunk_err}")
                    # Continue with other chunks on non-JSON errors

            # Add the last segment if there's anything left
            if current_segment:
                story_segments.append(current_segment)

            # Check if we have images, if not, consider it an error condition
            if not image_data:
                print("\n⚠️ No images were generated in the stream response")
                image_load_failures = max_image_retries  # Force a retry
                
            if image_load_failures >= max_image_retries:
                print(f"\n⚠️ Too many image failures ({image_load_failures}), will retry story generation")
                return None  # Signal retry needed
                
        except Exception as stream_err:
            print(f"\n⚠️ Error with streaming API: {stream_err}")
            print("🔄 Falling back to non-streaming API...")
            
            # Fallback to non-streaming API
            response = model.generate_content(
                contents,
                stream=False,
                **generate_params
            )
            
            # Process non-streaming response
            story_text = ""
            story_segments = []
            image_data = []
            
            # Extract text content
            if hasattr(response, 'text'):
                story_text = response.text
                print(story_text)
                
                # Split text into story segments
                segments = re.split(r'\n\s*\n', story_text)
                story_segments = [s for s in segments if s.strip()]
            
            # Extract image content
            if hasattr(response, 'parts'):
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        try:
                            # Display image if in notebook
                            if in_notebook:
                                display(IPythonImage(
                                    data=base64.b64decode(part.inline_data.data),
                                    format=part.inline_data.mime_type.split('/')[-1]
                                ))
                            
                            # Save image data for later use
                            image_data.append({
                                'data': part.inline_data.data,
                                'mime_type': part.inline_data.mime_type
                            })
                        except Exception as img_err:
                            print(f"\n⚠️ Error processing image: {img_err}")
                            image_load_failures += 1
            
            # Check if we have enough content
            if not story_segments or not image_data:
                print("\n⚠️ Not enough content in non-streaming response")
                return None  # Signal retry needed

        # Extract the story title from the first segment
        title = story_segments[0].split('\n')[0].strip() if story_segments else "Generated Story"
        
        # Clean up the segments (remove any titles, etc.)
        segments_cleaned = []
        for idx, segment in enumerate(story_segments):
            if idx == 0:
                # First segment might have the title
                lines = segment.split('\n')
                if len(lines) > 1:
                    segments_cleaned.append('\n'.join(lines[1:]).strip())
                else:
                    segments_cleaned.append(segment.strip())
            else:
                segments_cleaned.append(segment.strip())
        
        # Save the images to disk
        temp_dir = tempfile.mkdtemp()
        image_files = []
        
        for idx, img in enumerate(image_data):
            try:
                # Determine file extension based on mime type
                ext = img['mime_type'].split('/')[-1]
                if ext == 'jpeg':
                    ext = 'jpg'  # Standardize to .jpg
                
                # Create the image file path
                image_path = os.path.join(temp_dir, f"image_{idx+1}.{ext}")
                
                # Convert base64 to image and save
                img_data = base64.b64decode(img['data'])
                img_file = open(image_path, 'wb')
                img_file.write(img_data)
                img_file.close()
                
                print(f"✅ Saved image {idx+1} to {image_path}")
                image_files.append(image_path)
                
                # Verify the image is valid by trying to open it
                try:
                    with PILImage.open(image_path) as test_img:
                        width, height = test_img.size
                        print(f"   Image dimensions: {width}x{height}")
                except Exception as verify_err:
                    print(f"⚠️ Saved image {idx+1} is not valid: {verify_err}")
                    image_load_failures += 1
            except Exception as save_err:
                print(f"⚠️ Error saving image {idx+1}: {save_err}")
                image_load_failures += 1
        
        # Check if we had too many image failures
        if image_load_failures >= max_image_retries:
            print(f"⚠️ Too many image failures ({image_load_failures})")
            return None  # Signal retry needed
            
        # Make sure we have enough story segments for a good video
        if len(segments_cleaned) < 6:
            print(f"⚠️ Not enough story segments (got {len(segments_cleaned)}, need at least 6)")
            return None  # Signal retry needed
        
        print("\n✅ Successfully generated story with images!")
        
        # Return all the information
        return {
            'title': title,
            'story_text': story_text,
            'story_segments': segments_cleaned,
            'image_files': image_files,
            'temp_dir': temp_dir,
            'prompt_text': prompt_text,
            'image_data': image_data  # Include the raw image data
        }
        
    except Exception as e:
        print(f"🔴 Error in generate function: {e}")
        traceback.print_exc()
        return None
