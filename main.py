# main.py
# This is the main entry point for the application

# 1. Install required libraries
# !pip install -q google-generativeai IPython
# !pip install -q pillow
# !pip install -q google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
# !pip install -q kokoro>=0.9.2 soundfile
# !apt-get -qq -y install espeak-ng > /dev/null 2>&1

# 2. Import libraries
import os
import sys
import base64
import datetime
import tempfile
from IPython.display import display, HTML, Image
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

# Import from our modules
from config.settings import safety_settings
from utils.drive_utils import test_google_drive_api, download_file_from_google_drive, upload_text_file_to_drive
from generators.prompt_generator import generate_prompt
from generators.story_generator import retry_story_generation, generate
from generators.audio_generator import generate_audio
from generators.video_generator import generate_video
from metadata.seo_generator import generate_seo_metadata, default_seo_metadata, generate_thumbnail

# Run the test before executing any models
print("\n--- Testing Google Drive API Integration ---")
api_test_result = test_google_drive_api()
if not api_test_result:
    print("⚠️ Warning: Google Drive API test failed. Some features related to Google Drive may not work properly.")
else:
    print("✅ Google Drive API integration is ready to use.")

def upload_to_google_drive(output_path, story_text, prompt_text, image_files, metadata=None, thumbnail_path=None):
    """
    Uploads the generated video and metadata to Google Drive.
    
    Args:
        output_path: Path to the generated video file
        story_text: The story text
        prompt_text: The original prompt
        image_files: List of image files
        metadata: SEO metadata dictionary
        thumbnail_path: Path to the thumbnail image
    """
    if not output_path or not os.path.exists(output_path):
        print("⚠️ No video file available for upload")
        return

    try:
        print("\n--- Saving Video to Google Drive using API ---")

        # Create a temporary directory for credentials
        temp_dir = tempfile.mkdtemp()
        
        # Download and use credentials from Google Drive link instead of hardcoding them
        credentials_file_id = "152LtocR_Lvll37IW3GXJWAowLS02YBF2"
        credentials_file_path = os.path.join(temp_dir, "drive_credentials.json")
        
        print("⏳ Downloading Google Drive API credentials from the provided link...")
        try:
            # Download the credentials file
            download_file_from_google_drive(credentials_file_id, credentials_file_path)
            print(f"✅ Credentials file downloaded to: {credentials_file_path}")
            
            # Set up credentials from the downloaded file
            credentials = service_account.Credentials.from_service_account_file(
                credentials_file_path,
                scopes=['https://www.googleapis.com/auth/drive']
            )
            print("✅ Successfully loaded credentials from downloaded file")
            
        except Exception as e:
            print(f"⚠️ Error downloading or loading credentials: {e}")
            print("Attempting to continue with alternative methods...")
            raise

        drive_service = build('drive', 'v3', credentials=credentials)

        # Create main folder if it doesn't exist
        main_folder_name = 'GeminiStories'
        main_folder_id = None

        # Check if main folder exists
        query = f"name='{main_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query).execute()
        items = results.get('files', [])

        if not items:
            # Create main folder
            print(f"Creating main folder '{main_folder_name}'...")
            folder_metadata = {
                'name': main_folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            main_folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            main_folder_id = main_folder.get('id')
        else:
            main_folder_id = items[0]['id']

        print(f"✅ Using main folder: {main_folder_name} (ID: {main_folder_id})")

        # Generate a timestamp for the folder name
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        story_folder_name = f"{timestamp}_story"

        # Create a folder for this story
        story_folder_metadata = {
            'name': story_folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [main_folder_id]
        }

        story_folder = drive_service.files().create(body=story_folder_metadata, fields='id').execute()
        story_folder_id = story_folder.get('id')
        print(f"✅ Created story folder: {story_folder_name} (ID: {story_folder_id})")

        # Generate SEO metadata if needed
        if not metadata:
            metadata = generate_seo_metadata(story_text, image_files, prompt_text)

        # Generate thumbnail if needed
        if not thumbnail_path:
            thumbnail_path = generate_thumbnail(image_files, story_text, metadata)

        # Upload video
        print("⏳ Uploading video to Google Drive...")
        video_metadata = {
            'name': 'video.mp4',
            'parents': [story_folder_id]
        }

        media = MediaFileUpload(output_path, mimetype='video/mp4', resumable=True)
        video_file = drive_service.files().create(
            body=video_metadata,
            media_body=media,
            fields='id'
        ).execute()

        print(f"✅ Video uploaded successfully (File ID: {video_file.get('id')})")

        # Upload metadata files
        # Title
        title_content = metadata['title']
        title_file_id = upload_text_file_to_drive(title_content, 'title.txt', story_folder_id, drive_service, temp_dir)

        # Description
        desc_content = metadata['description']
        desc_file_id = upload_text_file_to_drive(desc_content, 'description.txt', story_folder_id, drive_service, temp_dir)

        # Tags
        tags_content = '\n'.join(metadata['tags'])
        tags_file_id = upload_text_file_to_drive(tags_content, 'tags.txt', story_folder_id, drive_service, temp_dir)

        # Upload thumbnail if available
        if thumbnail_path and os.path.exists(thumbnail_path):
            thumb_metadata = {
                'name': 'thumbnail.jpg',
                'parents': [story_folder_id]
            }

            thumb_media = MediaFileUpload(thumbnail_path, mimetype='image/jpeg', resumable=True)
            thumb_file = drive_service.files().create(
                body=thumb_metadata,
                media_body=thumb_media,
                fields='id'
            ).execute()

            print(f"✅ Thumbnail uploaded successfully (File ID: {thumb_file.get('id')})")

        # Get a direct link to the folder
        folder_link = f"https://drive.google.com/drive/folders/{story_folder_id}"
        print(f"\n✅ All files uploaded successfully to Google Drive!")
        print(f"📁 Folder link: {folder_link}")

        # Display a summary of the uploaded content
        print("\n--- Upload Summary ---")
        print(f"• Video: video.mp4")
        print(f"• Title: {metadata['title']}")
        print(f"• Description: {len(metadata['description'])} characters")
        print(f"• Tags: {len(metadata['tags'])} tags")
        if thumbnail_path and os.path.exists(thumbnail_path):
            print(f"• Thumbnail: thumbnail.jpg")
            
        # Important: Completely stop execution after successful upload
        print("\n✅✅✅ Upload to Google Drive successful! Script execution will stop now to prevent unnecessary retries.")
        print("🛑 Terminating script execution...")
        
        # Force exit the script with success code
        sys.exit(0)

    except ImportError as ie:
        print(f"⚠️ Required libraries for Google Drive API not installed: {ie}")
        print("💡 To use Google Drive API, install these packages:")
        print("   pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2")
        print("\n💡 You can manually download the video from the temporary location:")
        print(f"   {output_path}")
        
    except Exception as e:
        print(f"⚠️ Error uploading to Google Drive: {e}")
        print("💡 You can manually download the video from the temporary location:")
        print(f"   {output_path}")
        
def offer_direct_download(output_path):
    """Offers a direct download link for the video if Google Drive upload failed"""
    # Skip this section if we already uploaded to Google Drive
    # This section is only for when Google Drive upload was not available or failed
    if 'drive_service' not in locals() and output_path and os.path.exists(output_path):
        print("\n--- Download Video ---")
        # Get file size in MB
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)

        if file_size_mb < 50:  # Only try data URL method for files under 50MB
            with open(output_path, "rb") as video_file:
                video_data = video_file.read()
                b64_data = base64.b64encode(video_data).decode()
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                display(HTML(f"""
                <a href="data:video/mp4;base64,{b64_data}"
                   download="gemini_story_{timestamp}.mp4"
                   style="
                       display: inline-block;
                       padding: 10px 20px;
                       background-color: #4CAF50;
                       color: white;
                       text-decoration: none;
                       border-radius: 5px;
                       font-weight: bold;
                       margin-top: 10px;
                   ">
                   Download Video ({file_size_mb:.1f} MB)
                </a>
                """))
        else:
            print("⚠️ Video file is too large for direct download in notebook.")
            print(f"Video size: {file_size_mb:.1f} MB")
            print("Please download it from the location shown above.")

def main():
    """Main function that orchestrates the entire process"""
    print("--- Starting generation (attempting 16:9 via prompt) ---")
    
    # Generate the story using the retry mechanism
    result = retry_story_generation(use_prompt_generator=True)
    
    # Check if we have all required outputs
    if not result or not result.get("story_text") or not result.get("image_files"):
        print("⚠️ Story generation failed or incomplete")
        return
    
    # Generate audio
    story_text = result["story_text"]
    image_files = result["image_files"]
    temp_dir = result.get("temp_dir") or tempfile.mkdtemp()
    prompt_text = result.get("prompt_text", "")
    
    # Generate audio for the story
    audio_results = generate_audio(story_text, temp_dir)
    if not audio_results:
        print("⚠️ Audio generation failed")
        return
    
    # Generate video from images and audio
    video_results = generate_video(story_text, image_files, audio_results, temp_dir)
    if not video_results:
        print("⚠️ Video generation failed")
        return
    
    # Generate SEO metadata
    metadata = generate_seo_metadata(story_text, image_files, prompt_text)
    
    # Generate thumbnail
    thumbnail_path = generate_thumbnail(image_files, story_text, metadata)
    
    # Upload to Google Drive
    output_path = video_results.get("output_path")
    if output_path and os.path.exists(output_path):
        upload_to_google_drive(
            output_path=output_path,
            story_text=story_text,
            prompt_text=prompt_text,
            image_files=image_files,
            metadata=metadata,
            thumbnail_path=thumbnail_path
        )
    
    # Offer direct download as fallback
    offer_direct_download(output_path)
    
    print("--- Generation function finished ---")

# Execute the main function
if __name__ == "__main__":
    main()
