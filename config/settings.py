# config/settings.py
import os
import random
import google.generativeai as genai

# Load API key from environment
def get_api_key():
    """Randomly selects an API key from the provided environment variable (comma-separated)."""
    # Get the environment variable containing the API key(s)
    api_keys_env = os.environ.get("GEMINI_API_KEY", "")
    
    # If no API key in environment, use the hardcoded list as fallback
    if not api_keys_env:
        print("⚠️ No API key found in GEMINI_API_KEY environment variable, using fallback keys")
        api_keys = [
            "AIzaSyAqbqE86FKFXS6t5qrpXJVj9jAf-arQ1Js",
            "AIzaSyDVmSA9ricHVEzo6v1gj-crkuaJvQD72yw",
            "AIzaSyDNeeKDXnwGF7MYhFrnFoD9VL-ecvO5mEE",
            "AIzaSyAHvAdcSoRmeXB9xJjvvdXKtXw3dHSmJiQ",
            "AIzaSyC_XqbLjFQnLXfo26J-RX_WDx59H4ql9Qs",
            "AIzaSyC8FuTNC3FxLs0Qx2ciRoLwxjOrLGqOB5A",
            "AIzaSyBL8KngLHXOY0rSk5R4awta1tfDl6xC8rM"
        ]
    else:
        # Split by commas if multiple keys are provided
        api_keys = [key.strip() for key in api_keys_env.split(",") if key.strip()]
    
    # Count available keys
    key_count = len(api_keys)
    print(f"✅ Randomly selected one of {key_count} available API keys")
    
    # Randomly select one key
    selected_key = random.choice(api_keys)
    print(f"✅ Found API Key: ...{selected_key[-4:]}")
    
    return selected_key

# Configure the API client
try:
    # Get an API key
    api_key = get_api_key()
    
    # Configure the API client with the API key - new method for 0.8.4
    genai.configure(api_key=api_key)
except Exception as e:
    print(f"❌ Error initializing API: {e}")

# Define default safety settings that allow creative content
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]
print(f"⚙️ Defined Safety Settings: {safety_settings}")
