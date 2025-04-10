# Children's Story Generator

An AI-powered application that automatically generates children's stories with images, converts them to audio, and combines everything into a complete video with visual effects. The final output is uploaded to Google Drive for distribution.

## Features

- **AI Story Generation**: Creates unique children's stories using Google's Gemini AI models
- **Image Generation**: Generates images for each scene of the story
- **Text-to-Speech**: Converts the story to high-quality audio narration
- **Video Creation**: Combines images and audio into a video with professional transitions and effects
- **SEO Metadata**: Generates YouTube-friendly titles, descriptions, and tags
- **Thumbnail Creation**: Creates an attractive thumbnail for the video
- **Google Drive Integration**: Automatically uploads all content to Google Drive

## Project Structure

```
project/
├── main.py                 # Entry point that orchestrates the entire process
├── config/
│   ├── __init__.py
│   └── settings.py         # API keys and safety settings
├── utils/
│   ├── __init__.py
│   ├── drive_utils.py      # Google Drive functionality
│   ├── api_utils.py        # API retry mechanisms
│   └── media_utils.py      # Story text processing utilities
├── generators/
│   ├── __init__.py
│   ├── prompt_generator.py # Prompt generation
│   ├── story_generator.py  # Story generation with images
│   ├── audio_generator.py  # Text-to-speech conversion
│   └── video_generator.py  # Video creation with effects
└── metadata/
    ├── __init__.py
    └── seo_generator.py    # SEO metadata and thumbnail generation
```

## Requirements

- Python 3.7 or higher
- FFmpeg (for video creation)
- Google Gemini API key
- Google Drive API credentials (for uploading)

## Installation

1. Clone this repository:
```
git clone <repository-url>
cd <repository-folder>
```

2. Install required dependencies:
```
pip install -r requirements.txt
```

3. Install FFmpeg (required for video generation):
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - **MacOS**: `brew install ffmpeg`
   - **Linux**: `apt-get install ffmpeg`

4. Set up Gemini API access:
   - Get an API key from [Google AI Studio](https://makersuite.google.com/)
   - The application will randomly select from available API keys or you can set your own

5. (Optional) Set up Google Drive API:
   - Follow the [Google Drive API Python quickstart](https://developers.google.com/drive/api/quickstart/python)
   - Download credentials JSON file (service account key)
   - The application includes a test function to verify Drive API functionality

## Usage

Run the main script:

```
python main.py
```

The application will:
1. Generate a creative prompt for a children's story
2. Use that prompt to generate a story with accompanying images
3. Clean and structure the story text
4. Convert story to speech audio
5. Process and resize images
6. Apply visual effects and create a video
7. Generate SEO metadata and a thumbnail
8. Upload everything to Google Drive
9. Provide direct download options if needed

## Configuration

- Modify the API keys in `config/settings.py` if needed
- Adjust safety settings to control content generation
- Change prompt templates in `generators/prompt_generator.py` to customize story themes

## Troubleshooting

- **No images generated**: The model may sometimes generate text descriptions instead of images. The application will automatically retry.
- **Google Drive upload fails**: Check your credentials and internet connection. A local download option is provided as fallback.
- **FFmpeg errors**: Ensure FFmpeg is correctly installed and accessible in your PATH.

## License

[MIT License](LICENSE)

## Run on Google Colab

Copy and paste the following code into a Google Colab notebook cell to set up and run this project:

```python
# Clone the repository
!git clone https://github.com/abhiraman9012/Children-s-Story-Generator.git
%cd Children-s-Story-Generator

# Install required dependencies
!pip install -r requirements.txt

# Install FFmpeg (required for video generation)
!apt-get update
!apt-get install -y ffmpeg

# Set your Gemini API Key (replace with your actual key)
import os
os.environ["GEMINI_API_KEY"] = "your-api-key-here"

# Run the application
!python main.py
```

## Acknowledgments

- Google Gemini models for AI content generation
- Kokoro for text-to-speech conversion
- FFmpeg for video processing
