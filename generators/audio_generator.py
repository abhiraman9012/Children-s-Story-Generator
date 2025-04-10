# generators/audio_generator.py
import os
import numpy as np
import soundfile as sf
import warnings
from IPython.display import Audio, display
from kokoro import KPipeline
from utils.media_utils import collect_complete_story

# Suppress specific warnings
warnings.filterwarnings("ignore", message="dropout option adds dropout after all but last recurrent layer")
warnings.filterwarnings("ignore", message="`torch.nn.utils.weight_norm` is deprecated")

def generate_audio(story_text, temp_dir):
    """
    Generates audio for a story using Kokoro TTS.
    
    Args:
        story_text: The text of the story to convert to speech
        temp_dir: Temporary directory to store the audio file
        
    Returns:
        Path to the generated audio file
    """
    print("\n--- Starting Text-to-Speech Generation with Kokoro ---")
    
    try:
        # First collect and clean the complete story
        complete_story = collect_complete_story(story_text)
        
        print("⏳ Converting complete story to speech...")
        print("Story to be converted:", complete_story[:100] + "...")
        
        # Initialize Kokoro pipeline with explicit repo_id to suppress warning
        try:
            pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
        except Exception as e:
            # Fallback if the explicit repo_id causes issues
            print(f"Warning: Could not initialize with explicit repo_id: {e}")
            pipeline = KPipeline(lang_code='a')
        
        try:
            # Generate audio for the complete story
            print("Full story length:", len(complete_story), "characters")
            generator = pipeline(complete_story, voice='af_heart')
            
            # Save the complete audio file
            audio_path = os.path.join(temp_dir, "complete_story.wav")
            
            # Process and save all audio chunks
            all_audio = []
            for _, (gs, ps, audio) in enumerate(generator):
                all_audio.append(audio)
            
            # Combine all audio chunks
            if all_audio:
                combined_audio = np.concatenate(all_audio)
                sf.write(audio_path, combined_audio, 24000)
                print(f"✅ Complete story audio saved to: {audio_path}")
                print("🔊 Playing complete story audio:")
                # Try to display audio, but handle the case where display might not be available (non-notebook)
                try:
                    display(Audio(data=combined_audio, rate=24000))
                except Exception as display_error:
                    print(f"Note: Audio generated but cannot display in current environment: {display_error}")
                
                return {
                    "audio_path": audio_path,
                    "combined_audio": combined_audio,
                    "sample_rate": 24000
                }
            else:
                print("⚠️ No audio chunks were generated")
                return None
                
        except Exception as e:
            print(f"⚠️ Error in text-to-speech generation: {e}")
            return None
            
    except Exception as e:
        print(f"⚠️ Error in audio generation: {e}")
        return None
