import os
import tempfile
import shutil
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, HttpUrl
import yt_dlp
import ffmpeg
import asyncio
from datetime import datetime

app = FastAPI(title="YouTube Video Trimmer API")

# Configure CORS with simpler settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=False,  # Disable credentials for now
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

class VideoRequest(BaseModel):
    url: HttpUrl
    start_time: str  # Format: HH:MM:SS
    end_time: str    # Format: HH:MM:SS

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/video-info")
async def get_info(url: str):
    """Get video information"""
    return get_video_info(url)

@app.post("/api/trim-video")
async def trim_video(request: VideoRequest, background_tasks: BackgroundTasks):
    """Trim video and return download link"""
    # Validate times
    try:
        start_seconds = time_to_seconds(request.start_time)
        end_seconds = time_to_seconds(request.end_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM:SS")
    
    # Get video info to validate duration
    video_info = get_video_info(str(request.url))
    if end_seconds > video_info['duration']:
        raise HTTPException(
            status_code=400,
            detail=f"End time exceeds video duration ({video_info['duration']} seconds)"
        )
    
    if start_seconds >= end_seconds:
        raise HTTPException(status_code=400, detail="Start time must be before end time")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(tempfile.gettempdir(), "video-trimmer")
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"trimmed_video_{timestamp}.mp4"
    output_path = os.path.join(output_dir, output_filename)
    
    # Process video
    await download_and_trim_video(str(request.url), request.start_time, request.end_time, output_path)
    
    # Clean up old files (keep only last 10 files)
    files = sorted(os.listdir(output_dir), key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
    if len(files) > 10:
        for old_file in files[:-10]:
            try:
                os.remove(os.path.join(output_dir, old_file))
            except:
                pass
    
    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename=output_filename,
        background=background_tasks
    )

def time_to_seconds(time_str: str) -> int:
    """Convert HH:MM:SS to seconds"""
    h, m, s = map(int, time_str.split(':'))
    return h * 3600 + m * 60 + s

def get_video_info(url: str) -> dict:
    """Get video information using yt-dlp"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'format': 'bv*[height<=480][height>=360][ext=mp4]+ba[ext=m4a]/b[height<=480][height>=360][ext=mp4]/b[height<=480][height>=360]',  # Target 360p-480p
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'no_color': True,
        'geo_bypass': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['web'],
                'player_skip': ['configs'],
            }
        },
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown Title'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error fetching video info: {str(e)}")

async def download_and_trim_video(url: str, start_time: str, end_time: str, output_path: str):
    """Download and trim the video using yt-dlp and ffmpeg"""
    # Create temporary directory for downloads
    with tempfile.TemporaryDirectory() as temp_dir:
        # Download video
        ydl_opts = {
            'format': 'bv*[height<=480][height>=360][ext=mp4]+ba[ext=m4a]/b[height<=480][height>=360][ext=mp4]/b[height<=480][height>=360]',  # Target 360p-480p
            'outtmpl': os.path.join(temp_dir, 'video.%(ext)s'),
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'no_color': True,
            'geo_bypass': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['web'],
                    'player_skip': ['configs'],
                }
            },
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            },
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'merge_output_format': 'mp4',
            'retries': 3,
            'fragment_retries': 3,
            'skip_unavailable_fragments': True,
            'keepvideo': False,
            'writethumbnail': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'postprocessor_args': [
                '-c:v', 'copy',
                '-c:a', 'copy',
            ],
            'concurrent_fragment_downloads': 3,
            'throttledratelimit': 100000,
            'socket_timeout': 30,
            'extractor_retries': 3,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Find the downloaded file
            video_file = next((f for f in os.listdir(temp_dir) if f.startswith('video.')), None)
            if not video_file:
                raise Exception("Video file not found after download")
            
            input_path = os.path.join(temp_dir, video_file)
            
            # Convert times to seconds
            start_seconds = time_to_seconds(start_time)
            end_seconds = time_to_seconds(end_time)
            duration = end_seconds - start_seconds
            
            # Trim video using ffmpeg
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(
                stream,
                output_path,
                ss=start_seconds,
                t=duration,
                acodec='copy',
                vcodec='copy'
            )
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 