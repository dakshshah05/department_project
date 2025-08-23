# Utility functions for file operations - DO NOT MODIFY unless you know what you're doing
import json
import os

def read_json(path: str):
    """
    Read JSON file and return data
    Used for loading: users, rooms, faculty data
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}")

def write_json(path: str, data):
    """
    Write data to JSON file with proper formatting
    Used for saving: room bookings, user data
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def ensure_dir(path: str):
    """
    Create directory if it doesn't exist
    Used for: upload folders
    """
    os.makedirs(path, exist_ok=True)
