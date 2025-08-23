# Audit trail functionality for booking history
from datetime import datetime
import uuid
from utils.io import append_json_array, read_json

AUDIT_FILE = "data/audit_log.json"

def log_audit_event(actor_email: str, action: str, entity_type: str, entity_id: str, details: dict = None):
    """Log an audit event"""
    event = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "actor": actor_email,
        "action": action,  # BOOK, CANCEL, EDIT, UPLOAD, DELETE, CREATE_ALBUM
        "entity_type": entity_type,  # ROOM_BOOKING, MEDIA, ALBUM
        "entity_id": entity_id,
        "details": details or {}
    }
    append_json_array(AUDIT_FILE, event)

def get_audit_history(entity_type: str = None, entity_id: str = None, actor: str = None):
    """Get audit history with optional filters"""
    try:
        events = read_json(AUDIT_FILE)
        if not isinstance(events, list):
            return []
        
        filtered = events
        if entity_type:
            filtered = [e for e in filtered if e.get('entity_type') == entity_type]
        if entity_id:
            filtered = [e for e in filtered if e.get('entity_id') == entity_id]
        if actor:
            filtered = [e for e in filtered if e.get('actor') == actor]
        
        # Sort by timestamp (newest first)
        return sorted(filtered, key=lambda x: x.get('timestamp', ''), reverse=True)
    except:
        return []

def get_booking_history(room: str, day: str, slot: str):
    """Get history for a specific room booking"""
    entity_id = f"{room}|{day}|{slot}"
    return get_audit_history("ROOM_BOOKING", entity_id)
