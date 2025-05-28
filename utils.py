import os
import re
import tempfile
import requests
import yt_dlp
from typing import Dict, Optional, List, Tuple
import streamlit as st

def validate_youtube_url(url: str) -> bool:
    """
    Validate if the provided URL is a valid YouTube URL.
    
    Args:
        url (str): The URL to validate
        
    Returns:
        bool: True if valid YouTube URL, False otherwise
    """
    youtube_patterns = [
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/',
        r'(https?://)?(www\.)?youtu\.be/',
        r'(https?://)?(www\.)?youtube\.com/watch\?v=',
        r'(https?://)?(www\.)?youtube\.com/embed/',
        r'(https?://)?(www\.)?youtube\.com/v/',
    ]
    
    return any(re.match(pattern, url) for pattern in youtube_patterns)

def get_video_info(url: str) -> Optional[Dict]:
    """
    Extract video information from YouTube URL.
    
    Args:
        url (str): YouTube URL
        
    Returns:
        Optional[Dict]: Video information or None if failed
    """
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            return {
                'title': info.get('title', 'Unknown Title'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'upload_date': info.get('upload_date', ''),
                'description': info.get('description', ''),
                'formats': info.get('formats', [])
            }
    except Exception as e:
        st.error(f"Error extracting video info: {str(e)}")
        return None

def format_duration(seconds: int) -> str:
    """
    Convert seconds to human-readable duration format.
    
    Args:
        seconds (int): Duration in seconds
        
    Returns:
        str: Formatted duration string
    """
    if seconds == 0:
        return "Unknown"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def format_file_size(bytes_size: int) -> str:
    """
    Convert bytes to human-readable file size.
    
    Args:
        bytes_size (int): Size in bytes
        
    Returns:
        str: Formatted file size string
    """
    if bytes_size == 0:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

def get_available_formats(video_info: Dict) -> List[Dict]:
    """
    Extract and organize available download formats.
    
    Args:
        video_info (Dict): Video information dictionary
        
    Returns:
        List[Dict]: List of available formats with quality info
    """
    formats = video_info.get('formats', [])
    organized_formats = []
    
    # Video formats
    video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
    
    # Audio-only formats
    audio_formats = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
    
    # Organize video formats
    for fmt in video_formats:
        if fmt.get('ext') in ['mp4', 'webm', 'mkv']:
            organized_formats.append({
                'format_id': fmt.get('format_id'),
                'ext': fmt.get('ext', 'mp4'),
                'quality': fmt.get('height', 'Unknown'),
                'filesize': fmt.get('filesize', 0),
                'type': 'video',
                'note': fmt.get('format_note', ''),
                'fps': fmt.get('fps', 0)
            })
    
    # Organize audio formats
    for fmt in audio_formats:
        if fmt.get('ext') in ['mp3', 'm4a', 'webm']:
            organized_formats.append({
                'format_id': fmt.get('format_id'),
                'ext': fmt.get('ext', 'mp3'),
                'quality': fmt.get('abr', 'Unknown'),
                'filesize': fmt.get('filesize', 0),
                'type': 'audio',
                'note': fmt.get('format_note', ''),
                'abr': fmt.get('abr', 0)
            })
    
    return organized_formats

class DownloadProgressHook:
    """Progress hook class for yt-dlp download progress tracking."""
    
    def __init__(self, progress_bar, status_text):
        self.progress_bar = progress_bar
        self.status_text = status_text
        self.last_percent = 0
    
    def __call__(self, d):
        if d['status'] == 'downloading':
            if 'total_bytes' in d:
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                self.progress_bar.progress(percent / 100)
                self.status_text.text(f"Downloaded: {format_file_size(d['downloaded_bytes'])} / {format_file_size(d['total_bytes'])} ({percent:.1f}%)")
            elif '_percent_str' in d:
                percent_str = d['_percent_str'].strip('%')
                try:
                    percent = float(percent_str)
                    self.progress_bar.progress(percent / 100)
                    self.status_text.text(f"Progress: {percent:.1f}%")
                except:
                    self.status_text.text("Downloading...")
        elif d['status'] == 'finished':
            self.progress_bar.progress(1.0)
            self.status_text.text("Download completed!")

def download_video(url: str, format_id: str, output_path: str, progress_hook) -> Tuple[bool, str]:
    """
    Download video with specified format.
    
    Args:
        url (str): YouTube URL
        format_id (str): Format ID to download
        output_path (str): Output directory path
        progress_hook: Progress callback function
        
    Returns:
        Tuple[bool, str]: Success status and message/file path
    """
    try:
        ydl_opts = {
            'format': format_id,
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        # Find the downloaded file
        files = os.listdir(output_path)
        if files:
            return True, os.path.join(output_path, files[0])
        else:
            return False, "Download completed but file not found"
            
    except Exception as e:
        return False, f"Download failed: {str(e)}"

def create_download_directory() -> str:
    """
    Create a temporary directory for downloads.
    
    Returns:
        str: Path to the download directory
    """
    download_dir = tempfile.mkdtemp(prefix="youtube_download_")
    return download_dir
