# Media processing utilities for thumbnails and metadata
import os
from PIL import Image
import streamlit as st
from utils.io import ensure_dir, read_json

THUMBNAILS_DIR = "uploads/thumbnails"
SETTINGS_FILE = "data/settings.json"

def create_thumbnail(image_path: str, filename: str):
    """Create thumbnail for image file"""
    try:
        settings = read_json(SETTINGS_FILE)
        if not settings.get("thumbnails", {}).get("enabled", True):
            return None
        
        ensure_dir(THUMBNAILS_DIR)
        
        # Generate thumbnail path
        name, ext = os.path.splitext(filename)
        thumb_filename = f"{name}_thumb{ext}"
        thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename)
        
        # Skip if thumbnail already exists
        if os.path.exists(thumb_path):
            return thumb_path
        
        # Create thumbnail
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Get thumbnail settings
            max_size = tuple(settings.get("thumbnails", {}).get("max_size", [200, 200]))
            quality = settings.get("thumbnails", {}).get("quality", 85)
            
            # Create thumbnail
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(thumb_path, quality=quality, optimize=True)
            
        return thumb_path
    except Exception as e:
        print(f"❌ Thumbnail creation failed for {filename}: {e}")
        return None

def get_video_metadata(video_path: str):
    """Get basic video metadata (duration, size)"""
    try:
        # For production, you'd use ffprobe or similar
        # This is a simple fallback
        stat = os.stat(video_path)
        size_mb = stat.st_size / (1024 * 1024)
        
        return {
            "duration": "Unknown",  # Would need ffprobe for real duration
            "size_mb": round(size_mb, 2),
            "format": os.path.splitext(video_path)[1].lower()
        }
    except Exception as e:
        print(f"❌ Video metadata extraction failed: {e}")
        return {"duration": "Unknown", "size_mb": 0, "format": "mp4"}

def get_image_metadata(image_path: str):
    """Get basic image metadata"""
    try:
        with Image.open(image_path) as img:
            return {
                "dimensions": f"{img.width} x {img.height}",
                "format": img.format,
                "mode": img.mode
            }
    except Exception as e:
        print(f"❌ Image metadata extraction failed: {e}")
        return {"dimensions": "Unknown", "format": "Unknown", "mode": "Unknown"}
