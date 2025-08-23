# Email and Telegram notification system
import smtplib
from email.message import EmailMessage
import requests
from datetime import datetime, timedelta
import streamlit as st
from utils.io import read_json

SETTINGS_FILE = "data/settings.json"

def load_settings():
    """Load notification settings"""
    try:
        return read_json(SETTINGS_FILE)
    except:
        return {
            "notifications": {
                "email": {"enabled": False},
                "telegram": {"enabled": False}
            }
        }

def send_booking_confirmation(user_email: str, room: str, date_str: str, slot: str):
    """Send booking confirmation notification"""
    subject = f"Room Booking Confirmed: {room}"
    message = f"""
Your room booking has been confirmed:

📅 Room: {room}
📅 Date: {date_str}
⏰ Time: {slot}
👤 Booked by: {user_email}

This booking will automatically expire when the time slot ends.

Department Portal
"""
    
    _send_notification(subject, message, [user_email])
    _log_notification("BOOKING_CONFIRMATION", user_email, f"{room} - {date_str} {slot}")

def send_booking_reminder(user_email: str, room: str, date_str: str, slot: str):
    """Send booking reminder (30 minutes before)"""
    subject = f"Room Booking Reminder: {room} in 30 minutes"
    message = f"""
Reminder: Your room booking starts in 30 minutes

📅 Room: {room}
📅 Date: {date_str}
⏰ Time: {slot}

Please arrive on time. The room will automatically become available again after your slot ends.

Department Portal
"""
    
    _send_notification(subject, message, [user_email])
    _log_notification("BOOKING_REMINDER", user_email, f"{room} - {date_str} {slot}")

def send_booking_cancelled(user_email: str, room: str, date_str: str, slot: str, reason: str = ""):
    """Send booking cancellation notification"""
    subject = f"Room Booking Cancelled: {room}"
    message = f"""
Your room booking has been cancelled:

📅 Room: {room}
📅 Date: {date_str}
⏰ Time: {slot}
👤 Cancelled by: {user_email}
📝 Reason: {reason or "Not specified"}

The slot is now available for other users to book.

Department Portal
"""
    
    _send_notification(subject, message, [user_email])
    _log_notification("BOOKING_CANCELLATION", user_email, f"{room} - {date_str} {slot}")

def _send_notification(subject: str, message: str, recipients: list):
    """Internal notification sender"""
    settings = load_settings()
    
    # Email notification
    if settings.get("notifications", {}).get("email", {}).get("enabled"):
        _send_email(subject, message, recipients)
    else:
        print(f"[EMAIL DISABLED] {subject}")
        print(f"Recipients: {recipients}")
        print(f"Message: {message[:100]}...")
    
    # Telegram notification  
    if settings.get("notifications", {}).get("telegram", {}).get("enabled"):
        telegram_msg = f"🏛️ {subject}\n\n{message}"
        _send_telegram(telegram_msg)
    else:
        print(f"[TELEGRAM DISABLED] {subject}")

def _send_email(subject: str, body: str, recipients: list):
    """Send email using SMTP"""
    try:
        settings = load_settings()
        email_config = settings["notifications"]["email"]
        
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = email_config["from_email"]
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)
        
        with smtplib.SMTP(email_config["smtp_host"], email_config["smtp_port"]) as server:
            server.starttls()
            server.login(email_config["username"], email_config["password"])
            server.send_message(msg)
            
        print(f"✅ Email sent: {subject}")
    except Exception as e:
        print(f"❌ Email failed: {e}")

def _send_telegram(message: str):
    """Send Telegram message using bot API"""
    try:
        settings = load_settings()
        telegram_config = settings["notifications"]["telegram"]
        
        url = f"https://api.telegram.org/bot{telegram_config['bot_token']}/sendMessage"
        data = {
            "chat_id": telegram_config["chat_id"],
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        
        print(f"✅ Telegram sent: {message[:50]}...")
    except Exception as e:
        print(f"❌ Telegram failed: {e}")

def _log_notification(type_: str, recipient: str, context: str):
    """Log notification for audit trail"""
    print(f"📧 {type_}: {recipient} - {context}")
