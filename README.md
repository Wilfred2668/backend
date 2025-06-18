# YouTube Video Trimmer Backend

This is the backend service for the YouTube Video Trimmer application. It provides APIs for fetching video information and trimming YouTube videos.

## Features

- Fetch video information from YouTube URLs
- Download and trim videos using yt-dlp and ffmpeg
- Automatic cleanup of temporary files
- CORS enabled for frontend integration

## Prerequisites

- Python 3.8 or higher
- FFmpeg installed on your system
- pip (Python package manager)

## Installation

1. Install FFmpeg:

   - Windows: Download from https://ffmpeg.org/download.html
   - Linux: `sudo apt-get install ffmpeg`
   - macOS: `brew install ffmpeg`

2. Create a virtual environment (recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Server

1. Start the server:

   ```bash
   uvicorn main:app --reload
   ```

2. The server will start at `http://localhost:8000`

## API Endpoints

### GET /api/video-info

Get information about a YouTube video.

Query Parameters:

- `url`: YouTube video URL

Response:

```json
{
  "title": "Video Title",
  "duration": 120,
  "thumbnail": "thumbnail_url"
}
```

### POST /api/trim-video

Trim a YouTube video and return a download link.

Request Body:

```json
{
  "url": "https://www.youtube.com/watch?v=...",
  "start_time": "00:00:00",
  "end_time": "00:01:30"
}
```

Response:

- Returns the trimmed video file for download

## Deployment on Render

1. Create a new Web Service on Render
2. Connect your repository
3. Set the following:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Environment Variables: None required

## Error Handling

The API returns appropriate HTTP status codes and error messages:

- 400: Bad Request (invalid input)
- 500: Internal Server Error

## Security Notes

- In production, update CORS settings to only allow your frontend domain
- Consider implementing rate limiting
- Add authentication if needed
