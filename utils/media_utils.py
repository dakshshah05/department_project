# Enhanced media processing utilities with optimized image sizes
import os
from PIL import Image
import streamlit as st
from utils.io import ensure_dir, read_json

THUMBNAILS_DIR = "uploads/thumbnails"
SETTINGS_FILE = "data/settings.json"

def create_thumbnail(image_path: str, filename: str):
    """Create optimized thumbnail for image file"""
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
        
        # Create optimized thumbnail
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Optimized thumbnail settings for better viewing
            max_size = (200, 200)  # Smaller size for better performance
            quality = 85
            
            # Create thumbnail maintaining aspect ratio
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save optimized thumbnail
            img.save(thumb_path, quality=quality, optimize=True)
            
        return thumb_path
    except Exception as e:
        print(f"❌ Thumbnail creation failed for {filename}: {e}")
        return None

def create_display_image(image_path: str, filename: str, max_width=400):
    """Create display-optimized image for web viewing"""
    try:
        name, ext = os.path.splitext(filename)
        display_filename = f"{name}_display{ext}"
        display_path = os.path.join(THUMBNAILS_DIR, display_filename)
        
        # Skip if display image already exists
        if os.path.exists(display_path):
            return display_path
        
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Calculate new size maintaining aspect ratio
            width, height = img.size
            if width > max_width:
                new_height = int((height * max_width) / width)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # Save optimized display image
            img.save(display_path, quality=90, optimize=True)
            
        return display_path
    except Exception as e:
        print(f"❌ Display image creation failed for {filename}: {e}")
        return None

def get_video_metadata(video_path: str):
    """Get enhanced video metadata"""
    try:
        stat = os.stat(video_path)
        size_mb = stat.st_size / (1024 * 1024)
        
        # For production, you'd use ffprobe for real metadata
        # This is a simplified version
        return {
            "duration": "Unknown",  # Would need ffprobe
            "size_mb": round(size_mb, 2),
            "format": os.path.splitext(video_path)[1].lower(),
            "resolution": "Unknown",  # Would need ffprobe
            "codec": "Unknown"  # Would need ffprobe
        }
    except Exception as e:
        print(f"❌ Video metadata extraction failed: {e}")
        return {"duration": "Unknown", "size_mb": 0, "format": "mp4"}

def get_image_metadata(image_path: str):
    """Get enhanced image metadata"""
    try:
        with Image.open(image_path) as img:
            # Calculate file size
            stat = os.stat(image_path)
            size_kb = stat.st_size / 1024
            
            return {
                "dimensions": f"{img.width} x {img.height}",
                "format": img.format,
                "mode": img.mode,
                "size_kb": round(size_kb, 2),
                "aspect_ratio": round(img.width / img.height, 2) if img.height > 0 else 0
            }
    except Exception as e:
        print(f"❌ Image metadata extraction failed: {e}")
        return {"dimensions": "Unknown", "format": "Unknown", "mode": "Unknown"}

def optimize_image_for_web(image_path: str, output_path: str, max_size=(800, 600), quality=85):
    """Optimize image for web display"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Resize if larger than max_size
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save optimized
            img.save(output_path, 'JPEG', quality=quality, optimize=True)
            
        return True
    except Exception as e:
        print(f"❌ Image optimization failed: {e}")
        return False

def get_file_size_human_readable(file_path: str):
    """Get human readable file size"""
    try:
        size_bytes = os.path.getsize(file_path)
        
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes/(1024**2):.1f} MB"
        else:
            return f"{size_bytes/(1024**3):.1f} GB"
    except:
        return "Unknown"

def validate_image_file(file_path: str):
    """Validate if file is a valid image"""
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except:
        return False

def validate_video_file(file_path: str):
    """Basic video file validation"""
    try:
        # Basic validation - check file extension and size
        valid_extensions = ['.mp4', '.avi', '.mov', '.wmv']
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext not in valid_extensions:
            return False
        
        # Check if file has reasonable size (not 0 bytes)
        if os.path.getsize(file_path) == 0:
            return False
        
        return True
    except:
        return False
