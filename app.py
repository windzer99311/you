import streamlit as st
import os
import shutil
from utils import (
    validate_youtube_url, 
    get_video_info, 
    format_duration, 
    format_file_size, 
    get_available_formats,
    download_video,
    create_download_directory,
    DownloadProgressHook
)

def main():
    """Main Streamlit application."""
    
    # Page configuration
    st.set_page_config(
        page_title="YouTube Video Downloader",
        page_icon="📹",
        layout="wide"
    )
    
    # Main title
    st.title("📹 YouTube Video Downloader")
    st.markdown("Download YouTube videos in various formats with real-time progress tracking.")
    
    # Initialize session state
    if 'video_info' not in st.session_state:
        st.session_state.video_info = None
    if 'download_formats' not in st.session_state:
        st.session_state.download_formats = []
    if 'download_in_progress' not in st.session_state:
        st.session_state.download_in_progress = False
    
    # URL input section
    st.header("🔗 Enter YouTube URL")
    url_input = st.text_input(
        "YouTube URL:",
        placeholder="https://www.youtube.com/watch?v=...",
        help="Enter a valid YouTube video URL"
    )
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        fetch_info_btn = st.button("📋 Get Video Info", disabled=st.session_state.download_in_progress)
    
    with col2:
        if url_input:
            if validate_youtube_url(url_input):
                st.success("✅ Valid YouTube URL")
            else:
                st.error("❌ Invalid YouTube URL")
    
    # Fetch video information
    if fetch_info_btn and url_input:
        if not validate_youtube_url(url_input):
            st.error("Please enter a valid YouTube URL")
            return
        
        with st.spinner("Fetching video information..."):
            video_info = get_video_info(url_input)
            
            if video_info:
                st.session_state.video_info = video_info
                st.session_state.download_formats = get_available_formats(video_info)
                st.success("Video information fetched successfully!")
                st.rerun()
            else:
                st.error("Failed to fetch video information. Please check the URL and try again.")
    
    # Display video information
    if st.session_state.video_info:
        st.header("📺 Video Information")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Display thumbnail
            if st.session_state.video_info['thumbnail']:
                st.image(
                    st.session_state.video_info['thumbnail'], 
                    caption="Video Thumbnail",
                    use_column_width=True
                )
        
        with col2:
            # Display video details
            st.subheader(st.session_state.video_info['title'])
            
            info_col1, info_col2 = st.columns(2)
            
            with info_col1:
                st.write(f"**📺 Channel:** {st.session_state.video_info['uploader']}")
                st.write(f"**⏱️ Duration:** {format_duration(st.session_state.video_info['duration'])}")
            
            with info_col2:
                if st.session_state.video_info['view_count']:
                    st.write(f"**👀 Views:** {st.session_state.video_info['view_count']:,}")
                if st.session_state.video_info['upload_date']:
                    upload_date = st.session_state.video_info['upload_date']
                    formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
                    st.write(f"**📅 Upload Date:** {formatted_date}")
        
        # Format selection and download
        st.header("⬬ Download Options")
        
        if st.session_state.download_formats:
            # Organize formats by type
            video_formats = [f for f in st.session_state.download_formats if f['type'] == 'video']
            audio_formats = [f for f in st.session_state.download_formats if f['type'] == 'audio']
            
            format_col1, format_col2 = st.columns(2)
            
            with format_col1:
                st.subheader("🎥 Video Formats")
                if video_formats:
                    video_options = []
                    video_format_map = {}
                    
                    for fmt in video_formats:
                        quality = f"{fmt['quality']}p" if str(fmt['quality']).isdigit() else str(fmt['quality'])
                        size_info = f" ({format_file_size(fmt['filesize'])})" if fmt['filesize'] else ""
                        fps_info = f" {fmt['fps']}fps" if fmt['fps'] else ""
                        option_text = f"{fmt['ext'].upper()} - {quality}{fps_info}{size_info}"
                        video_options.append(option_text)
                        video_format_map[option_text] = fmt['format_id']
                    
                    selected_video = st.selectbox(
                        "Choose video format:",
                        options=video_options,
                        index=0,
                        disabled=st.session_state.download_in_progress
                    )
                    
                    if st.button("📥 Download Video", disabled=st.session_state.download_in_progress):
                        download_format(url_input, video_format_map[selected_video], "video")
                else:
                    st.info("No video formats available")
            
            with format_col2:
                st.subheader("🎵 Audio Formats")
                if audio_formats:
                    audio_options = []
                    audio_format_map = {}
                    
                    for fmt in audio_formats:
                        quality = f"{fmt['quality']} kbps" if str(fmt['quality']).isdigit() else str(fmt['quality'])
                        size_info = f" ({format_file_size(fmt['filesize'])})" if fmt['filesize'] else ""
                        option_text = f"{fmt['ext'].upper()} - {quality}{size_info}"
                        audio_options.append(option_text)
                        audio_format_map[option_text] = fmt['format_id']
                    
                    selected_audio = st.selectbox(
                        "Choose audio format:",
                        options=audio_options,
                        index=0,
                        disabled=st.session_state.download_in_progress
                    )
                    
                    if st.button("📥 Download Audio", disabled=st.session_state.download_in_progress):
                        download_format(url_input, audio_format_map[selected_audio], "audio")
                else:
                    st.info("No audio formats available")
        else:
            st.warning("No download formats found for this video")

def download_format(url: str, format_id: str, download_type: str):
    """Handle the download process with progress tracking."""
    
    st.session_state.download_in_progress = True
    
    # Create download directory
    download_dir = create_download_directory()
    
    try:
        st.subheader(f"📥 Downloading {download_type.title()}...")
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Create progress hook
        progress_hook = DownloadProgressHook(progress_bar, status_text)
        
        # Download the video
        success, result = download_video(url, format_id, download_dir, progress_hook)
        
        if success:
            st.success("✅ Download completed successfully!")
            
            # Provide download link
            if os.path.exists(result):
                filename = os.path.basename(result)
                file_size = os.path.getsize(result)
                
                st.info(f"📁 **File:** {filename}")
                st.info(f"📊 **Size:** {format_file_size(file_size)}")
                
                # Read file and provide download button
                with open(result, 'rb') as file:
                    file_data = file.read()
                    
                st.download_button(
                    label="💾 Download File",
                    data=file_data,
                    file_name=filename,
                    mime="application/octet-stream"
                )
            else:
                st.warning("File downloaded but could not be located for download link")
        else:
            st.error(f"❌ Download failed: {result}")
    
    except Exception as e:
        st.error(f"❌ An error occurred during download: {str(e)}")
    
    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(download_dir)
        except:
            pass
        
        st.session_state.download_in_progress = False

if __name__ == "__main__":
    main()
