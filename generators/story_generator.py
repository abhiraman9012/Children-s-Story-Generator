# generators/story_generator.py
import os
import re
import json
import tempfile
import time
import threading
import traceback
from google import genai
from google.genai import types
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
    # Initialize variables that might be used later
    output_path = None
    story_text = None
    image_files = []

    try:
        client = genai.Client(
             api_key=os.environ.get("GEMINI_API_KEY"),
        )
        print("✅ Initializing client using genai.Client...")
    except AttributeError:
        print("🔴 FATAL ERROR: genai.Client is unexpectedly unavailable.")
        return
    except Exception as e:
        print(f"🔴 Error initializing client: {e}")
        return
    print("✅ Client object created successfully.")

    model = "gemini-2.0-flash-exp-image-generation"

    # --- Modified Prompt ---
    if use_prompt_generator:
        print("🧠 Using prompt generator model first...")
        # Use retry mechanism for generate_prompt
        generated_prompt = retry_api_call(generate_prompt, prompt_input)
        if generated_prompt and generated_prompt.strip():
            prompt_text = generated_prompt
            print("✅ Using AI-generated prompt for story and image creation")
        else:
            print("⚠️ Prompt generation failed or returned empty, using default prompt")
            prompt_text = """Generate a story about a white baby goat named Pip going on an adventure in a farm in a highly detailed 3d cartoon animation style. For each scene, generate a high-quality, photorealistic image **in landscape orientation suitable for a widescreen (16:9 aspect ratio) YouTube video**. Ensure maximum detail, vibrant colors, and professional lighting."""
    else:
        prompt_text = """Generate a story about a white baby goat named Pip going on an adventure in a farm in a highly detailed 3d cartoon animation style. For each scene, generate a high-quality, photorealistic image **in landscape orientation suitable for a widescreen (16:9 aspect ratio) YouTube video**. Ensure maximum detail, vibrant colors, and professional lighting."""
    # --- End Modified Prompt ---

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt_text),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_modalities=["image", "text"],
        response_mime_type="text/plain",
        safety_settings=safety_settings,
    )

    print(f"ℹ️ Using Model: {model}")
    print(f"📝 Using Prompt: {prompt_text}") # Show the modified prompt
    print(f"⚙️ Using Config (incl. safety): {generate_content_config}")
    print("⏳ Calling client.models.generate_content_stream...")

    try:
        # Create a temporary directory to store images and audio
        temp_dir = tempfile.mkdtemp()

        # Variables to collect story and images
        story_text = ""
        image_files = []

        try:
            # Flag to determine if we should use streaming or fallback approach
            use_streaming = True

            try:
                # Wrap the API call in the retry mechanism
                def attempt_stream_generation():
                    return client.models.generate_content_stream(
                        model=model,
                        contents=contents,
                        config=generate_content_config,
                    )

                stream = retry_api_call(attempt_stream_generation)

            except json.decoder.JSONDecodeError as je:
                print(f"⚠️ JSON decoding error during stream creation: {je}")
                print("Trying fallback to non-streaming API call...")
                use_streaming = False

                # Fallback to non-streaming version
                try:
                    # Wrap the fallback API call in the retry mechanism
                    def attempt_non_stream_generation():
                        return client.models.generate_content(
                            model=model,
                            contents=contents,
                            config=generate_content_config,
                        )

                    response = retry_api_call(attempt_non_stream_generation)

                    # Process the non-streaming response
                    print("Using non-streaming response instead")
                    image_found = False

                    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                image_found = True
                                inline_data = part.inline_data
                                image_data = inline_data.data
                                mime_type = inline_data.mime_type

                                # Save image to a temporary file
                                img_path = os.path.join(temp_dir, f"image_{len(image_files)}.jpg")
                                with open(img_path, "wb") as f:
                                    f.write(image_data)
                                image_files.append(img_path)

                                print(f"\n\n🖼️ --- Image Received ({mime_type}) ---")
                                # Display image differently based on environment
                                if in_notebook:
                                    display(IPythonImage(data=image_data))
                                else:
                                    # For non-notebook environments, save and inform user
                                    image = PILImage.open(io.BytesIO(image_data))
                                    print(f"Image saved to {img_path} - {image.width}x{image.height}")
                                    # For debugging, could also show image dimensions and type
                                    print(f"Image type: {image.format}, Mode: {image.mode}, Size: {image.size}")
                                print("--- End Image ---\n")
                            elif hasattr(part, 'text') and part.text:
                                print(part.text)
                                story_text += part.text

                    # Skip the streaming loop since we already processed the response
                    print("✅ Non-streaming processing complete.")
                    if not image_found:
                        print("⚠️ No images were found in the non-streaming response.")

                    # Continue with audio and video processing
                    image_found = True  # Set this to true to prevent early exit

                except Exception as e:
                    print(f"⚠️ Fallback API call also failed: {e}")
                    return

            except Exception as e:
                print(f"⚠️ Error creating stream: {e}")
                return

            # Only enter the streaming loop if we're using streaming
            if use_streaming:
                image_found = False
                print("--- Response Stream ---")

                # Track JSON parsing errors to decide when to fallback
                json_errors = 0
                max_json_errors = 5  # Allow up to 5 errors before giving up on streaming

                # Check for Image Description text instead of actual images
                contains_image_description = False

                try:
                    for chunk in stream:
                        try:
                            # If we get a raw string instead of parsed content
                            if isinstance(chunk, str):
                                print(chunk, end="")
                                story_text += chunk
                                # Check for image descriptions
                                if "**Image Description:**" in chunk:
                                    contains_image_description = True
                                continue

                            # Check if chunk has candidates
                            if not hasattr(chunk, 'candidates') or not chunk.candidates:
                                # Try to extract as much as possible from the chunk
                                if hasattr(chunk, 'text') and chunk.text:
                                    print(chunk.text, end="")
                                    story_text += chunk.text
                                    # Check for image descriptions
                                    if "**Image Description:**" in chunk.text:
                                        contains_image_description = True
                                continue

                            if not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
                                if hasattr(chunk, 'text') and chunk.text:
                                    print(chunk.text, end="")
                                    story_text += chunk.text
                                    # Check for image descriptions
                                    if "**Image Description:**" in chunk.text:
                                        contains_image_description = True
                                continue

                            part = chunk.candidates[0].content.parts[0]

                            if hasattr(part, 'inline_data') and part.inline_data:
                                image_found = True
                                inline_data = part.inline_data
                                image_data = inline_data.data
                                mime_type = inline_data.mime_type

                                # Save image to a temporary file
                                img_path = os.path.join(temp_dir, f"image_{len(image_files)}.jpg")
                                with open(img_path, "wb") as f:
                                    f.write(image_data)
                                image_files.append(img_path)

                                print(f"\n\n🖼️ --- Image Received ({mime_type}) ---")
                                # Display image differently based on environment
                                if in_notebook:
                                    display(IPythonImage(data=image_data))
                                else:
                                    # For non-notebook environments, save and inform user
                                    image = PILImage.open(io.BytesIO(image_data))
                                    print(f"Image saved to {img_path} - {image.width}x{image.height}")
                                    # For debugging, could also show image dimensions and type
                                    print(f"Image type: {image.format}, Mode: {image.mode}, Size: {image.size}")
                                print("--- End Image ---\n")
                            elif hasattr(part,'text') and part.text:
                                print(part.text, end="")
                                story_text += part.text
                                # Check for image descriptions
                                if "**Image Description:**" in part.text:
                                    contains_image_description = True
                        except json.decoder.JSONDecodeError as je:
                            print(f"\n⚠️ JSON decoding error in chunk: {je}")
                            json_errors += 1
                            if json_errors >= max_json_errors:
                                print(f"Too many JSON errors ({json_errors}), falling back to non-streaming mode...")
                                # Try to extract any text that might be in the raw response
                                try:
                                    if hasattr(chunk, '_response') and hasattr(chunk._response, 'text'):
                                        raw_text = chunk._response.text
                                        # Extract text content between markdown or code blocks if possible
                                        story_text += re.sub(r'```.*?```', '', raw_text, flags=re.DOTALL)
                                        print(f"Extracted {len(raw_text)} characters from raw response")
                                except Exception:
                                    pass
                                break  # Exit the streaming loop and use the fallback
                            continue  # Skip this chunk and continue with next
                        except Exception as e:
                            print(f"\n⚠️ Error processing chunk: {e}")
                            continue  # Skip this chunk and continue with next
                except Exception as e:
                    print(f"⚠️ Error in stream processing: {e}")
                    # If streaming failed completely, try the non-streaming fallback
                    if not story_text.strip() and json_errors > 0:
                        print("Stream processing failed, trying non-streaming fallback...")
                        try:
                            response = client.models.generate_content(
                                model=model,
                                contents=contents,
                                config=generate_content_config,
                            )

                            if response.candidates and response.candidates[0].content:
                                for part in response.candidates[0].content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        story_text += part.text

                            print("✅ Non-streaming fallback successful")
                        except Exception as fallback_error:
                            print(f"⚠️ Non-streaming fallback also failed: {fallback_error}")
        except Exception as e:
            print(f"⚠️ Error in stream creation: {e}")
            return

        print("\n" + "-"*20)
        if not image_found:
             print("⚠️ No images were found in the stream.")
        print("✅ Stream processing complete.")

        if not image_found or contains_image_description:
            if contains_image_description:
                print("\n⚠️ Model generated text descriptions instead of actual images. Restarting generation...")
                # Restart the entire generation process by recursively calling generate
                return generate(use_prompt_generator=use_prompt_generator, prompt_input=prompt_input)
            elif not image_found:
                print("⚠️ No images were found in the stream.")
        print("✅ Stream processing complete.")

        # After generating story and images
        return {
            "story_text": story_text,
            "image_files": image_files,
            "temp_dir": temp_dir,
            "prompt_text": prompt_text
        }

    except Exception as e:
        print(f"\n🛑 An error occurred during streaming or processing: {e}")
        import traceback
        traceback.print_exc()
        return None
