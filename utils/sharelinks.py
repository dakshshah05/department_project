# Time-limited share link generation
import hmac
import hashlib
import time
import base64
from urllib.parse import quote, unquote
from utils.io import read_json

SETTINGS_FILE = "data/settings.json"

def generate_share_link(file_path: str, expiry_hours: int = None):
    """Generate time-limited share link for a file"""
    try:
        settings = read_json(SETTINGS_FILE)
        secret_key = settings.get("share_links", {}).get("secret_key", "default-secret")
        default_hours = settings.get("share_links", {}).get("default_expiry_hours", 48)
        
        if expiry_hours is None:
            expiry_hours = default_hours
        
        # Calculate expiry timestamp
        expiry_timestamp = int(time.time()) + (expiry_hours * 3600)
        
        # Create payload
        payload = f"{file_path}|{expiry_timestamp}"
        
        # Generate signature
        signature = hmac.new(
            secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Encode for URL
        encoded_payload = base64.urlsafe_b64encode(payload.encode()).decode()
        
        return {
            "token": f"{encoded_payload}.{signature}",
            "expiry_timestamp": expiry_timestamp,
            "expiry_hours": expiry_hours
        }
    except Exception as e:
        print(f"❌ Share link generation failed: {e}")
        return None

def verify_share_link(token: str):
    """Verify and decode share link token"""
    try:
        settings = read_json(SETTINGS_FILE)
        secret_key = settings.get("share_links", {}).get("secret_key", "default-secret")
        
        # Split token
        encoded_payload, signature = token.split('.')
        
        # Decode payload
        payload = base64.urlsafe_b64decode(encoded_payload).decode()
        
        # Verify signature
        expected_signature = hmac.new(
            secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return None
        
        # Parse payload
        file_path, expiry_timestamp = payload.split('|')
        expiry_timestamp = int(expiry_timestamp)
        
        # Check expiry
        if time.time() > expiry_timestamp:
            return None
        
        return {
            "file_path": file_path,
            "expiry_timestamp": expiry_timestamp,
            "valid": True
        }
    except Exception as e:
        print(f"❌ Share link verification failed: {e}")
        return None

def is_link_expired(expiry_timestamp: int):
    """Check if share link has expired"""
    return time.time() > expiry_timestamp
