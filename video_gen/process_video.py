"""
Video Processing Module
This module provides functionality to remove watermarks from videos by covering them with a patch or image.
"""
import os
import tempfile
from typing import Optional
try:
    # Try moviepy 2.x import structure
    from moviepy import VideoFileClip, ColorClip, CompositeVideoClip, ImageClip
except ImportError:
    # Fall back to moviepy 1.x import structure
    from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip, ImageClip
import requests
import time


def remove_watermark_with_patch(
    video_input: str,
    output_path: Optional[str] = None,
    patch_width: int = 400,
    patch_height: int = 100,
    patch_color: tuple = (255, 255, 255),  # White
    position: str = "bottom-right",
    margin_x: int = 0,
    margin_y: int = 0
) -> str:
    """
    Remove watermark from video by covering it with a solid color patch.
    
    Args:
        video_input (str): Path or URL to the input video file
        output_path (str, optional): Path for the output video. If None, creates a temp file
        patch_width (int): Width of the patch in pixels (default: 400)
        patch_height (int): Height of the patch in pixels (default: 100)
        patch_color (tuple): RGB color of the patch (default: (255, 255, 255) - white)
        position (str): Position of the patch - "bottom-right", "bottom-left", "top-right", "top-left"
        margin_x (int): Horizontal margin from edge in pixels (default: 0)
        margin_y (int): Vertical margin from edge in pixels (default: 0)
        
    Returns:
        str: Path to the processed video file
        
    Raises:
        Exception: If video processing fails
        
    Example:
        >>> output = remove_watermark_with_patch("input.mp4", "output.mp4")
        >>> # Custom color and position
        >>> output = remove_watermark_with_patch("input.mp4", "output.mp4", 
        ...                                      patch_color=(0, 255, 0), position="top-left")
    """
    temp_video_path = None
    
    try:
        # If input is URL, download the video first
        if video_input.startswith(('http://', 'https://')):
            print(f"📥 Downloading video from URL...")
            temp_video_path = _download_video(video_input)
            video_path = temp_video_path
        else:
            video_path = video_input
        
        print(f"🎬 Loading video: {video_path}")
        
        # Load the video
        video = VideoFileClip(video_path)
        video_width, video_height = video.size
        
        print(f"📐 Video size: {video_width}x{video_height}")
        print(f"⏱️  Video duration: {video.duration:.2f} seconds")
        
        print(f"🎨 Creating solid color patch: {patch_color}")
        # Create a solid color patch
        patch = ColorClip(
            size=(patch_width, patch_height),
            color=patch_color,
            duration=video.duration
        )
        
        # Calculate patch position based on the specified location
        if position == "bottom-right":
            patch_x = video_width - patch_width - margin_x
            patch_y = video_height - patch_height - margin_y
        elif position == "bottom-left":
            patch_x = margin_x
            patch_y = video_height - patch_height - margin_y
        elif position == "top-right":
            patch_x = video_width - patch_width - margin_x
            patch_y = margin_y
        elif position == "top-left":
            patch_x = margin_x
            patch_y = margin_y
        else:
            raise ValueError(f"Invalid position: {position}. Use 'bottom-right', 'bottom-left', 'top-right', or 'top-left'")
        
        print(f"📍 Adding {patch_color} patch at position ({patch_x}, {patch_y})")
        
        # Position the patch (use with_position for moviepy 2.x, set_position for 1.x)
        try:
            patch = patch.with_position((patch_x, patch_y))
        except AttributeError:
            patch = patch.set_position((patch_x, patch_y))
        
        # Composite the patch over the video
        final_video = CompositeVideoClip([video, patch])
        
        # Determine output path
        if output_path is None:
            # Create temporary file
            temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            output_path = temp_output.name
            temp_output.close()
            print(f"💾 No output path specified, using temp file: {output_path}")
        
        print(f"⚙️  Processing video (this may take a while)...")
        
        # Write the result
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            logger=None  # Suppress moviepy's verbose output
        )
        
        # Close the clips to release resources
        video.close()
        patch.close()
        final_video.close()
        
        print(f"✅ Video processed successfully!")
        print(f"📁 Output saved to: {output_path}")
        
        # Clean up downloaded temp file if it exists
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
            print(f"🗑️  Cleaned up temporary video file")
        
        return output_path
        
    except Exception as e:
        print(f"❌ Error processing video: {str(e)}")
        
        # Clean up temp file on error
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        
        raise Exception(f"Failed to process video: {str(e)}")


def remove_watermark_with_image(
    video_input: str,
    overlay_image: str,
    output_path: Optional[str] = None,
    patch_width: int = 400,
    patch_height: int = 100,
    position: str = "bottom-right",
    margin_x: int = 0,
    margin_y: int = 0
) -> str:
    """
    Remove watermark from video by covering it with a custom image overlay.
    
    Args:
        video_input (str): Path or URL to the input video file
        overlay_image (str): Path or URL to image to overlay (PNG/JPG/GIF/WEBP) - REQUIRED
        output_path (str, optional): Path for the output video. If None, creates a temp file
        patch_width (int): Width to resize the image in pixels (default: 400)
        patch_height (int): Height to resize the image in pixels (default: 100)
        position (str): Position of the overlay - "bottom-right", "bottom-left", "top-right", "top-left"
        margin_x (int): Horizontal margin from edge in pixels (default: 0)
        margin_y (int): Vertical margin from edge in pixels (default: 0)
        
    Returns:
        str: Path to the processed video file
        
    Raises:
        Exception: If video processing fails
        
    Example:
        >>> # With local image
        >>> output = remove_watermark_with_image("input.mp4", "logo.png", "output.mp4")
        
        >>> # With image from URL
        >>> output = remove_watermark_with_image("input.mp4", 
        ...                                      "https://example.com/logo.png",
        ...                                      "output.mp4")
    """
    temp_video_path = None
    temp_image_path = None
    
    try:
        # Validate overlay_image is provided
        if not overlay_image:
            raise ValueError("overlay_image is required for remove_watermark_with_image(). Use remove_watermark_with_patch() for solid colors.")
        
        # If input is URL, download the video first
        if video_input.startswith(('http://', 'https://')):
            print(f"📥 Downloading video from URL...")
            temp_video_path = _download_video(video_input)
            video_path = temp_video_path
        else:
            video_path = video_input
        
        print(f"🎬 Loading video: {video_path}")
        
        # Load the video
        video = VideoFileClip(video_path)
        video_width, video_height = video.size
        
        print(f"📐 Video size: {video_width}x{video_height}")
        print(f"⏱️  Video duration: {video.duration:.2f} seconds")
        
        print(f"🖼️  Using image overlay: {overlay_image}")
        
        # If image is URL, download it first
        if overlay_image.startswith(('http://', 'https://')):
            print(f"📥 Downloading image from URL...")
            temp_image_path = _download_image(overlay_image)
            image_path = temp_image_path
        else:
            image_path = overlay_image
        
        # Load and resize the image to specified dimensions
        patch = ImageClip(image_path)
        patch = patch.resized(width=patch_width, height=patch_height)
        patch = patch.with_duration(video.duration)
        
        print(f"✅ Image loaded and resized to {patch_width}x{patch_height}")
        
        # Calculate patch position based on the specified location
        if position == "bottom-right":
            patch_x = video_width - patch_width - margin_x
            patch_y = video_height - patch_height - margin_y
        elif position == "bottom-left":
            patch_x = margin_x
            patch_y = video_height - patch_height - margin_y
        elif position == "top-right":
            patch_x = video_width - patch_width - margin_x
            patch_y = margin_y
        elif position == "top-left":
            patch_x = margin_x
            patch_y = margin_y
        else:
            raise ValueError(f"Invalid position: {position}. Use 'bottom-right', 'bottom-left', 'top-right', or 'top-left'")
        
        print(f"📍 Adding image overlay at position ({patch_x}, {patch_y})")
        
        # Position the patch (use with_position for moviepy 2.x, set_position for 1.x)
        try:
            patch = patch.with_position((patch_x, patch_y))
        except AttributeError:
            patch = patch.set_position((patch_x, patch_y))
        
        # Composite the patch over the video
        final_video = CompositeVideoClip([video, patch])
        
        # Determine output path
        if output_path is None:
            # Create temporary file
            temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            output_path = temp_output.name
            temp_output.close()
            print(f"📝 No output path specified, using temp file: {output_path}")
        
        # Write the output video
        print(f"🎬 Writing output video...")
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            logger=None  # Suppress moviepy's verbose output
        )
        
        # Close the clips to release resources
        video.close()
        patch.close()
        final_video.close()
        
        print(f"✅ Video processed successfully!")
        print(f"📁 Output saved to: {output_path}")
        
        # Clean up downloaded temp files if they exist
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
            print(f"🗑️  Cleaned up temporary video file")
        
        if temp_image_path and os.path.exists(temp_image_path):
            os.remove(temp_image_path)
            print(f"🗑️  Cleaned up temporary image file")
        
        return output_path
        
    except Exception as e:
        print(f"❌ Error processing video: {str(e)}")
        
        # Clean up temp files on error
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        if temp_image_path and os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        
        raise Exception(f"Failed to process video: {str(e)}")


def _download_video(video_url: str) -> str:
    """
    Download video from URL to a temporary file.
    
    Args:
        video_url (str): URL of the video to download
        
    Returns:
        str: Path to the downloaded temporary file
    """
    try:
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_path = temp_file.name
        temp_file.close()
        
        # Download the video
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Show progress
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"📥 Download progress: {progress:.1f}%", end='\r')
        
        print(f"\n✅ Video downloaded to: {temp_path}")
        return temp_path
        
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise Exception(f"Failed to download video: {str(e)}")


def _download_image(image_url: str) -> str:
    """
    Download image from URL to a temporary file.
    
    Args:
        image_url (str): URL of the image to download
        
    Returns:
        str: Path to the downloaded temporary file
    """
    try:
        # Determine image extension from URL or default to .png
        parsed_url = image_url.lower()
        if '.jpg' in parsed_url or '.jpeg' in parsed_url:
            suffix = '.jpg'
        elif '.png' in parsed_url:
            suffix = '.png'
        elif '.gif' in parsed_url:
            suffix = '.gif'
        elif '.webp' in parsed_url:
            suffix = '.webp'
        else:
            suffix = '.png'  # Default to PNG
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_path = temp_file.name
        temp_file.close()
        
        # Download the image
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Show progress
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"🖼️  Image download progress: {progress:.1f}%", end='\r')
        
        print(f"\n✅ Image downloaded to: {temp_path}")
        return temp_path
        
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise Exception(f"Failed to download image: {str(e)}")


def remove_watermark_from_video(
    video_input: str,
    output_path: Optional[str] = None,
    patch_width: int = 400,
    patch_height: int = 100,
    patch_color: tuple = (255, 255, 255),
    position: str = "bottom-right",
    margin_x: int = 0,
    margin_y: int = 0,
    overlay_image: Optional[str] = None
) -> str:
    """
    Remove watermark from video - wrapper function for backward compatibility.
    Automatically chooses between patch or image overlay based on parameters.
    
    Args:
        video_input (str): Path or URL to the input video file
        output_path (str, optional): Path for the output video
        patch_width (int): Width of the patch/image in pixels
        patch_height (int): Height of the patch/image in pixels
        patch_color (tuple): RGB color of the patch (only used if no overlay_image)
        position (str): Position - "bottom-right", "bottom-left", "top-right", "top-left"
        margin_x (int): Horizontal margin from edge in pixels
        margin_y (int): Vertical margin from edge in pixels
        overlay_image (str, optional): Path or URL to image overlay (if provided, uses image instead of patch)
        
    Returns:
        str: Path to the processed video file
        
    Example:
        >>> # With solid color patch
        >>> remove_watermark_from_video("input.mp4", "output.mp4")
        
        >>> # With image overlay
        >>> remove_watermark_from_video("input.mp4", "output.mp4", overlay_image="logo.png")
    """
    if overlay_image:
        # Use image overlay function
        return remove_watermark_with_image(
            video_input=video_input,
            overlay_image=overlay_image,
            output_path=output_path,
            patch_width=patch_width,
            patch_height=patch_height,
            position=position,
            margin_x=margin_x,
            margin_y=margin_y
        )
    else:
        # Use solid color patch function
        return remove_watermark_with_patch(
            video_input=video_input,
            output_path=output_path,
            patch_width=patch_width,
            patch_height=patch_height,
            patch_color=patch_color,
            position=position,
            margin_x=margin_x,
            margin_y=margin_y
        )


def process_knolify_video(video_url: str, output_path: Optional[str] = None) -> str:
    """
    Convenience function specifically for processing Knolify videos.
    Uses default settings optimized for Knolify watermark removal.
    
    Args:
        video_url (str): URL of the Knolify video
        output_path (str, optional): Path for the output video
        
    Returns:
        str: Path to the processed video
        
    Example:
        >>> video_link = "https://knowlify-videos1.s3.us-west-2.amazonaws.com/video.mp4"
        >>> processed = process_knolify_video(video_link, "output.mp4")
    """
    return remove_watermark_from_video(
        video_input=video_url,
        output_path=output_path,
        patch_width=100,
        patch_height=50,
        patch_color=(255, 255, 255),  # White
        position="bottom-right",
        margin_x=0,
        margin_y=0
    )


# Test code - uncomment to run manual tests
if __name__ == "__main__":
    import time
    
    # start_time = time.time()
    # input_path = "C:\\Users\\shash\\Downloads\\911bffe8-934a-4f4b-b809-a5c7776816d6_combined.mp4"
    # output_path = "C:\\Users\\shash\\PycharmProjects\\pratinidhi-ai-backend\\math_tutor\\processed_video_image_5.mp4"
    # image_path = "C:\\Users\\shash\\PycharmProjects\\pratinidhi-ai-backend\\resources\\Educado.jpg"

    # # Test with solid color patch
    # output = remove_watermark_from_video(
    #     video_input=input_path,
    #     output_path=output_path
    # )

    # # Test with image overlay
    # output = remove_watermark_from_video(
    #     video_input=input_path,
    #     output_path=output_path,
    #     patch_width=120,
    #     patch_height=60,
    #     overlay_image=image_path
    # )
    # print(f"Processed video saved at: {output}")
    # print(f"Processing Time: {time.time() - start_time:.2f} seconds")
    
    print("ℹ️  This module contains video processing functions.")
    print("   Run demo_automated_video.py for interactive demo.")