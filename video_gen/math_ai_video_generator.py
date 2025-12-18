"""
Math AI Video Generator Module
This module generates video explanations for math problems using Knolify's APIs.
Supports both Grant (fast) and Prism (high-quality) APIs.
Uses WebSocket connection for real-time video generation with progress updates.
"""
import asyncio
import websockets
import json
import os
from typing import Dict, Optional
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Knolify WebSocket endpoint (same for both Grant and Prism)
KNOLIFY_WEBSOCKET_URL = "wss://50fa8sjxo9.execute-api.us-west-2.amazonaws.com/production"


async def _send_video_generation_request(
    task: str, 
    api_key: str, 
    api_type: str = "prism",
    background_color: Optional[str] = None,
    quality: str = "high"
) -> Dict:
    """
    Send a video generation request to Knolify's API via WebSocket.
    
    Args:
        task (str): The instruction/prompt for video generation
        api_key (str): Knolify API key
        api_type (str): API type - "grant" (fast) or "prism" (high-quality)
        background_color (str, optional): Background color for video (Prism only), e.g., "#FFFFFF"
        quality (str): Video quality for Prism - "low", "medium", "high", "production"
        
    Returns:
        dict: Response containing video_link, vtt_file, and status
        
    Raises:
        Exception: If video generation fails or connection errors occur
    """
    try:
        print(f"🔌 Connecting to Knolify WebSocket ({api_type.upper()} API)...")
        
        async with websockets.connect(KNOLIFY_WEBSOCKET_URL) as websocket:
            # Prepare payload based on API type
            if api_type.lower() == "prism":
                payload = {
                    "action": "Pre-Rendered",
                    "task": task,
                    "api_key": api_key,
                    "quality": quality
                }
                # Add background_color for Prism if provided
                if background_color:
                    payload["background_color"] = background_color
            else:
                # Grant API (default/fast)
                payload = {
                    "action": "finetuned_live_gen",
                    "task": task,
                    "api_key": api_key
                }
            
            print("📤 Sending video generation request...")
            print(f"📋 Payload: {json.dumps(payload, indent=2)}")
            await websocket.send(json.dumps(payload))
            
            # Listen for responses
            print("👂 Listening for responses...\n")
            while True:
                try:
                    response = await websocket.recv()
                    print(f"📨 Received raw response: {response}")
                    data = json.loads(response)
                    print(f"📦 Parsed data: {json.dumps(data, indent=2)}\n")
                    
                    # Handle different response types
                    if data.get("type") == "progress":
                        progress = data.get("progress", 0)
                        message = data.get("message", "Processing...")
                        print(f"⏳ Progress: {progress}% - {message}")
                        
                    elif data.get("type") == "error":
                        error_msg = data.get("message", "Unknown error")
                        error_code = data.get("error_code", "UNKNOWN")
                        print(f"❌ Error: {error_code} - {error_msg}")
                        raise Exception(f"Video generation failed: {error_msg}")
                    
                    # Check if response contains video link (Knolify's actual response format)
                    elif data.get("link") and data.get("vtt_link"):
                        print("✅ Video generation completed successfully!")
                        return {
                            "video_link": data.get("link"),
                            "vtt_file": data.get("vtt_link"),
                            "srt_file": data.get("srt_link"),
                            "status": "completed"
                        }
                    
                    # Alternative response format
                    elif data.get("video_link") and data.get("vtt_file"):
                        print("✅ Video generation completed successfully!")
                        return {
                            "video_link": data.get("video_link"),
                            "vtt_file": data.get("vtt_file"),
                            "srt_file": data.get("srt_file"),
                            "status": "completed"
                        }
                        
                    elif data.get("status") == "completed":
                        print("✅ Video generation completed successfully!")
                        return {
                            "video_link": data.get("video_link"),
                            "vtt_file": data.get("vtt_file"),
                            "status": data.get("status")
                        }
                        
                    elif data.get("status") == "failed":
                        print("❌ Video generation failed")
                        raise Exception("Video generation failed")
                    else:
                        print(f"⚠️  Unknown response format - continuing to listen...")
                        
                except websockets.exceptions.ConnectionClosed:
                    print("❌ WebSocket connection closed unexpectedly")
                    raise Exception("Connection closed before completion")
                    
    except Exception as e:
        print(f"❌ Error in video generation: {str(e)}")
        raise


def generate_math_ai_video(
    math_problem: str, 
    api_key: Optional[str] = None, 
    api_type: str = "prism",
    background_color: Optional[str] = None,
    quality: str = "high",
    remove_watermark: bool = False, 
    output_dir: Optional[str] = None
) -> Dict:
    """
    Generate an AI video explanation for a math problem and its solution.
    
    Args:
        math_problem (str): The math problem to explain
        api_key (str, optional): Knolify API key. If not provided, reads from KNOLIFY_API_KEY env variable
        api_type (str): API to use - "prism" (high-quality) or "grant" (fast). Default: "prism"
        background_color (str, optional): Background color for video (hex format, e.g., "#FFFFFF"). 
                                          Only supported by Prism API.
        quality (str): Video quality for Prism - "low", "medium", "high", "production". Default: "high"
        remove_watermark (bool): If True, downloads and processes video to remove watermark (default: False)
        output_dir (str, optional): Directory to save processed video. If None, uses temp directory
        
    Returns:
        dict: Response containing:
            - video_link (str): URL to the generated video
            - vtt_file (str): URL to the subtitle file
            - srt_file (str): URL to the SRT subtitle file
            - status (str): Generation status
            - processed_video_path (str): Path to processed video (only if remove_watermark=True)
            - watermark_removed (bool): Whether watermark was successfully removed
            
    Raises:
        ValueError: If API key is missing or inputs are invalid
        Exception: If video generation fails
        
    Example:
        >>> # Using Prism API with background color
        >>> result = generate_math_ai_video(
        ...     math_problem="Solve for x: 2x + 5 = 15",
        ...     api_type="prism",
        ...     background_color="#1a1a2e",
        ...     quality="high"
        ... )
        >>> print(result["video_link"])
        
        >>> # Using Grant API (faster)
        >>> result = generate_math_ai_video(
        ...     math_problem="Solve for x: 2x + 5 = 15",
        ...     api_type="grant"
        ... )
    """
    # Validate inputs
    if not math_problem or not math_problem.strip():
        raise ValueError("Math problem cannot be empty")
    
    # Get API key
    if api_key is None:
        api_key = os.getenv("KNOLIFY_API_KEY")
    
    if not api_key:
        raise ValueError("KNOLIFY_API_KEY not found in environment variables")
    
    # Construct the task prompt for video generation
    task = f"""Create a clear and engaging video explanation for the following math problem:

                Problem: {math_problem}

                You'd better make sure the calculation is correct.
                Please explain each step clearly with visual demonstrations and ensure the mathematical notation is properly displayed."""
    
    print(f"🎬 Generating video for math problem: {math_problem[:50]}...")
    print(f"📝 Using {api_type.upper()} API" + (f" with background color: {background_color}" if background_color else ""))
    print(f"📝 Full task being sent to Knolify:")
    print(f"{task}\n")
    
    # Run the async function
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            _send_video_generation_request(
                task=task, 
                api_key=api_key,
                api_type=api_type,
                background_color=background_color,
                quality=quality
            )
        )
        loop.close()
        
        print(f"✅ Video generated successfully!")
        print(f"🎥 Video Link: {result.get('video_link')}")
        print(f"📄 VTT File: {result.get('vtt_file')}")
        
        # Process video to remove watermark if requested
        if remove_watermark:
            try:
                print(f"\n🎨 Processing video to remove watermark...")
                
                # Import here to avoid circular dependency
                from math_tutor.process_video import remove_watermark_from_video
                
                # Determine output path
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    # Generate unique filename
                    import uuid
                    output_filename = f"processed_{uuid.uuid4().hex[:8]}.mp4"
                    output_path = os.path.join(output_dir, output_filename)
                else:
                    output_path = None  # Will use temp file
                
                # Download and process the video
                processed_path = remove_watermark_from_video(
                    video_input=result.get('video_link'),
                    output_path=output_path,
                    patch_width=300,
                    patch_height=70,
                    patch_color=(255, 255, 255),
                    position="bottom-right",
                    margin_x=0,
                    margin_y=0
                )
                
                print(f"✅ Watermark removed successfully!")
                print(f"📁 Processed video saved to: {processed_path}")
                
                # Add processed video info to result
                result['processed_video_path'] = processed_path
                result['watermark_removed'] = True
                
            except Exception as watermark_error:
                print(f"❌ Failed to remove watermark: {str(watermark_error)}")
                result['watermark_removed'] = False
                result['watermark_error'] = str(watermark_error)
        
        return result
        
    except Exception as e:
        print(f"❌ Failed to generate video: {str(e)}")
        raise Exception(f"Video generation failed: {str(e)}")