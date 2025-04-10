# generators/prompt_generator.py
import os
import re
import google.generativeai as genai
from utils.api_utils import retry_api_call

def generate_prompt(prompt_input="Create a children's story with a different animal character and a unique adventure theme. Be creative with the setting and storyline.", use_streaming=True):
    """
    Generates a story prompt using the gemini-2.0-flash-thinking-exp-01-21 model.

    Args:
        prompt_input: The input instructions for generating the prompt
        use_streaming: Whether to use streaming API or not

    Returns:
        The generated prompt text or None if generation fails
    """
    try:
        client = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY"),
        )
        print("✅ Initializing prompt generator client using genai.Client...")
    except Exception as e:
        print(f"🔴 Error initializing prompt generator client: {e}")
        return None

    model = "gemini-2.0-flash-thinking-exp-01-21"

    # Enhanced prompt input to ensure consistent structure with varied content
    enhanced_prompt_input = f"""
    Create a children's story prompt using EXACTLY this format:
    "Generate a story about [animal character] going on an adventure in [setting] in a highly detailed 3d cartoon animation style. For each scene, generate a high-quality, photorealistic image for each scene 3d images **in landscape orientation suitable for a widescreen (16:9 aspect ratio) YouTube video**. Ensure maximum detail, vibrant colors, and professional lighting."

    Replace [animal character] with any animal character (NOT a white baby goat named Pip).
    Replace [setting] with any interesting setting for the adventure.

    Do NOT change any other parts of the structure. Keep the exact beginning and ending exactly as shown.

    Your response should be ONLY the completed prompt with no additional text.

    Original guidance: {prompt_input}
    """

    contents = [
        {
            "role": "user",
            "parts": [
                {"text": enhanced_prompt_input}
            ]
        }
    ]
    generate_content_config = {
        "response_mime_type": "text/plain",
    }

    print(f"ℹ️ Using Prompt Generator Model: {model}")
    print(f"📝 Using Input: {prompt_input}")

    generated_prompt = ""

    try:
        if use_streaming:
            print("⏳ Generating prompt via streaming API...")
            stream = client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            )

            print("--- Prompt Generation Stream ---")
            for chunk in stream:
                try:
                    if hasattr(chunk, 'text') and chunk.text:
                        print(chunk.text, end="")
                        generated_prompt += chunk.text
                except Exception as e:
                    print(f"⚠️ Error processing prompt chunk: {e}")
                    continue
        else:
            print("⏳ Generating prompt via non-streaming API...")
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=generate_content_config,
            )

            if hasattr(response, 'text'):
                print("\n" + response.text)
                generated_prompt = response.text

        # Clean up any whitespace
        generated_prompt = generated_prompt.strip()

        # Validate the response format
        # It should start with "Generate a story about" and contain both [animal character] and [setting] replaced
        if "Generate a story about" not in generated_prompt or "going on an adventure in" not in generated_prompt:
            print("⚠️ Generated prompt doesn't match expected format")
            # Try to extract with regex if possible
            match = re.search(r'\"(.+?)\"', generated_prompt)
            if match:
                print("🔧 Extracting from quotes...")
                generated_prompt = match.group(1)
            
            if "Generate a story about" not in generated_prompt:
                print("⚠️ Still can't find expected format, generating fallback prompt...")
                return generate_fallback_prompt(prompt_input)
        
        print("\n✅ Prompt generation complete")
        return generated_prompt

    except Exception as e:
        print(f"⚠️ Error generating prompt: {e}")
        return generate_fallback_prompt(prompt_input)

def generate_fallback_prompt(prompt_input):
    """Generate a fallback prompt when AI generation fails."""
    import random
    
    animals = ["fox", "bear", "rabbit", "elephant", "tiger", "penguin", "koala", "turtle", "lion", "dolphin"]
    settings = ["enchanted forest", "snowy mountain", "deep ocean", "outer space", "desert oasis", 
                "ancient castle", "tropical island", "underwater cave", "cloud city", "magical garden"]
    
    animal = random.choice(animals)
    setting = random.choice(settings)
    
    fallback_prompt = f"Generate a story about a clever {animal} going on an adventure in a {setting} in a highly detailed 3d cartoon animation style. For each scene, generate a high-quality, photorealistic image for each scene 3d images **in landscape orientation suitable for a widescreen (16:9 aspect ratio) YouTube video**. Ensure maximum detail, vibrant colors, and professional lighting."
    
    print(f"🔄 Using fallback prompt with {animal} in {setting}")
    return fallback_prompt
