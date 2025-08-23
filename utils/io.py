# Enhanced JSON operations with append support
import json
import os
from typing import Any, Dict, List

def read_json(path: str):
    """Read JSON file and return data"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {} if path.endswith('.json') and 'index' in path else []
    except json.JSONDecodeError:
        return {} if path.endswith('.json') and 'index' in path else []

def write_json(path: str, data: Any):
    """Write data to JSON file with proper formatting"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def append_json_array(path: str, item: Dict):
    """Append item to JSON array file"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        write_json(path, [])
    
    data = read_json(path)
    if not isinstance(data, list):
        data = []
    
    data.append(item)
    write_json(path, data)

def ensure_dir(path: str):
    """Create directory if it doesn't exist"""
    os.makedirs(path, exist_ok=True)

def safe_listdir(path: str):
    """Safely list directory contents"""
    try:
        return sorted(os.listdir(path))
    except FileNotFoundError:
        return []
