# Enhanced notifications system with automated reminders
import streamlit as st
from datetime import datetime, timedelta
import json
from utils.io import read_json, write_json, append_json_array
from utils.notify import send_booking_confirmation, send_booking_reminder

NOTIFICATIONS_FILE = "data/notifications.json"

def main(user):
    """Enhanced notifications dashboard"""
    st.header("🔔 Notifications Center")
    st.markdown("---")
    
    # Tabs for different notification types
    tab1, tab2, tab3 = st.tabs(["📨 My Notifications", "⚙️ Settings", "📊 Notification History"])
    
    with tab1:
        show_user_notifications(user)
    
    with tab2:
        show_notification_settings(user)
    
    with tab3:
        show_notification_history(user)

def show_user_notifications(user):
    """Display user's notifications"""
    st.subheader("📨 Your Notifications")
    
    try:
        notifications = read_json(NOTIFICATIONS_FILE)
        user_notifications = [
            notif for notif in notifications 
            if notif.get('recipient') == user['email']
        ]
        
        if user_notifications:
            # Group by type
            unread_count = sum(1 for n in user_notifications if not n.get('read', False))
            st.info(f"📊 You have {unread_count} unread notifications out of {len(user_notifications)} total")
            
            for notification in sorted(user_notifications, key=lambda x: x.get('timestamp', ''), reverse=True)[:10]:
                show_notification_card(notification, user['email'])
        else:
            st.info("📭 No notifications found.")
            
    except Exception as e:
        st.error(f"❌ Error loading notifications: {e}")
    
    # Create test notification (for teachers)
    if user['role'].lower() == 'teacher':
        st.markdown("---")
        st.subheader("🧪 Test Notifications")
        
        if st.button("📧 Send Test Booking Confirmation"):
            create_test_notification(user['email'], "BOOKING_CONFIRMATION", "Test booking confirmed for Room1 on Monday 9-10AM")
            st.success("Test notification sent!")
            st.rerun()

def show_notification_card(notification, user_email):
    """Display individual notification card"""
    is_read = notification.get('read', False)
    notification_type = notification.get('type', 'INFO')
    
    # Icon mapping
    icons = {
        'BOOKING_CONFIRMATION': '✅',
        'BOOKING_REMINDER': '⏰',
        'BOOKING_CANCELLATION': '❌',
        'SYSTEM_ALERT': '🔔',
        'INFO': 'ℹ️'
    }
    
    icon = icons.get(notification_type, 'ℹ️')
    
    with st.container():
        col1, col2, col3 = st.columns([1, 8, 1])
        
        with col1:
            st.write(icon)
        
        with col2:
            if not is_read:
                st.markdown(f"**{notification.get('title', 'Notification')}**")
            else:
                st.write(notification.get('title', 'Notification'))
                
            st.caption(notification.get('message', ''))
            st.caption(f"📅 {notification.get('timestamp', 'Unknown time')}")
        
        with col3:
            if not is_read and st.button("✓", key=f"read_{notification.get('id')}", help="Mark as read"):
                mark_notification_as_read(notification.get('id'), user_email)
                st.rerun()
        
        st.markdown("---")

def show_notification_settings(user):
    """Notification preferences"""
    st.subheader("⚙️ Notification Settings")
    
    # Load user preferences
    try:
        settings = read_json("data/settings.json")
        user_prefs = settings.get('user_preferences', {}).get(user['email'], {})
    except:
        user_prefs = {}
    
    st.markdown("#### 📧 Email Notifications")
    email_booking_conf = st.checkbox(
        "Booking confirmations",
        value=user_prefs.get('email_booking_confirmations', True)
    )
    
    email_reminders = st.checkbox(
        "Booking reminders",
        value=user_prefs.get('email_reminders', True)
    )
    
    email_cancellations = st.checkbox(
        "Cancellation notices",
        value=user_prefs.get('email_cancellations', True)
    )
    
    st.markdown("#### 🔔 Push Notifications")
    push_enabled = st.checkbox(
        "Browser notifications",
        value=user_prefs.get('push_notifications', True)
    )
    
    st.markdown("#### ⏰ Reminder Settings")
    reminder_times = st.multiselect(
        "Send reminders:",
        ["1 day before", "1 hour before", "30 minutes before"],
        default=user_prefs.get('reminder_times', ["1 hour before", "30 minutes before"])
    )
    
    if st.button("💾 Save Settings"):
        # Save preferences
        new_prefs = {
            'email_booking_confirmations': email_booking_conf,
            'email_reminders': email_reminders,
            'email_cancellations': email_cancellations,
            'push_notifications': push_enabled,
            'reminder_times': reminder_times
        }
        
        save_user_preferences(user['email'], new_prefs)
        st.success("✅ Settings saved successfully!")

def show_notification_history(user):
    """Display notification history"""
    st.subheader("📊 Notification History")
    
    try:
        notifications = read_json(NOTIFICATIONS_FILE)
        user_notifications = [
            notif for notif in notifications 
            if notif.get('recipient') == user['email']
        ]
        
        if user_notifications:
            # Statistics
            total_notifications = len(user_notifications)
            read_notifications = sum(1 for n in user_notifications if n.get('read', False))
            unread_notifications = total_notifications - read_notifications
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📧 Total", total_notifications)
            with col2:
                st.metric("✅ Read", read_notifications)
            with col3:
                st.metric("📬 Unread", unread_notifications)
            
            # History table
            st.markdown("#### 📋 Recent Notifications")
            
            history_data = []
            for notif in sorted(user_notifications, key=lambda x: x.get('timestamp', ''), reverse=True)[:20]:
                history_data.append({
                    'Type': notif.get('type', 'INFO'),
                    'Title': notif.get('title', ''),
                    'Status': '✅ Read' if notif.get('read', False) else '📬 Unread',
                    'Date': notif.get('timestamp', '')[:19] if notif.get('timestamp') else 'Unknown'
                })
            
            if history_data:
                import pandas as pd
                df = pd.DataFrame(history_data)
                st.dataframe(df, use_container_width=True)
            
            # Clear history option
            st.markdown("---")
            if st.button("🗑️ Clear All Notifications", type="secondary"):
                clear_user_notifications(user['email'])
                st.success("All notifications cleared!")
                st.rerun()
                
        else:
            st.info("📭 No notification history available.")
            
    except Exception as e:
        st.error(f"❌ Error loading notification history: {e}")

def create_test_notification(recipient, notification_type, message):
    """Create a test notification"""
    notification = {
        'id': f"test_{datetime.now().timestamp()}",
        'recipient': recipient,
        'type': notification_type,
        'title': f"Test {notification_type.replace('_', ' ').title()}",
        'message': message,
        'timestamp': datetime.now().isoformat(),
        'read': False
    }
    
    try:
        notifications = read_json(NOTIFICATIONS_FILE)
        notifications.append(notification)
        write_json(NOTIFICATIONS_FILE, notifications)
    except:
        write_json(NOTIFICATIONS_FILE, [notification])

def mark_notification_as_read(notification_id, user_email):
    """Mark a notification as read"""
    try:
        notifications = read_json(NOTIFICATIONS_FILE)
        for notif in notifications:
            if notif.get('id') == notification_id and notif.get('recipient') == user_email:
                notif['read'] = True
                break
        write_json(NOTIFICATIONS_FILE, notifications)
    except Exception as e:
        st.error(f"Error marking notification as read: {e}")

def save_user_preferences(user_email, preferences):
    """Save user notification preferences"""
    try:
        settings = read_json("data/settings.json")
        if 'user_preferences' not in settings:
            settings['user_preferences'] = {}
        settings['user_preferences'][user_email] = preferences
        write_json("data/settings.json", settings)
    except Exception as e:
        st.error(f"Error saving preferences: {e}")

def clear_user_notifications(user_email):
    """Clear all notifications for a user"""
    try:
        notifications = read_json(NOTIFICATIONS_FILE)
        remaining_notifications = [
            notif for notif in notifications 
            if notif.get('recipient') != user_email
        ]
        write_json(NOTIFICATIONS_FILE, remaining_notifications)
    except Exception as e:
        st.error(f"Error clearing notifications: {e}")

def schedule_booking_reminders():
    """Schedule automated booking reminders (would run as background task)"""
    # This function would be called by a scheduler
    # For now, it's a placeholder for the reminder system
    pass

def send_push_notification(title, message, user_email):
    """Send browser push notification"""
    # JavaScript code for browser notifications
    js_code = f"""
    <script>
    if (Notification.permission === "granted") {{
        new Notification("{title}", {{
            body: "{message}",
            icon: "🔔"
        }});
    }} else if (Notification.permission !== "denied") {{
        Notification.requestPermission().then(function (permission) {{
            if (permission === "granted") {{
                new Notification("{title}", {{
                    body: "{message}",
                    icon: "🔔"
                }});
            }}
        }});
    }}
    </script>
    """
    
    st.components.v1.html(js_code, height=0)
