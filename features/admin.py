# Admin panel for system management
import streamlit as st
from utils.io import read_json, write_json
from utils.audit import get_audit_history
from utils.analytics_utils import generate_utilization_report

def main(user):
    """Admin panel interface"""
    st.header("⚙️ Admin Panel")
    st.markdown("---")
    
    if user["role"].lower() != "teacher":
        st.error("❌ Access denied. Admin panel is for teachers only.")
        return
    
    # Admin tabs
    tab1, tab2, tab3 = st.tabs(["📊 System Overview", "👥 User Management", "⚙️ Settings"])
    
    with tab1:
        show_system_overview()
    
    with tab2:
        show_user_management(user)
    
    with tab3:
        show_settings_management(user)

def show_system_overview():
    """Display system overview statistics"""
    st.subheader("📊 System Overview")
    
    try:
        # Load data
        rooms_data = read_json("data/rooms.json")
        faculty_data = read_json("data/faculty.json")
        users_data = read_json("data/users.json")
        audit_data = read_json("data/audit_log.json")
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🏠 Total Rooms", len(rooms_data))
        with col2:
            st.metric("👨‍🏫 Faculty Members", len(faculty_data))
        with col3:
            st.metric("👥 Total Users", len(users_data))
        with col4:
            st.metric("📋 Audit Events", len(audit_data))
        
        # Recent activity
        st.markdown("#### 📈 Recent Activity")
        recent_events = audit_data[-10:] if audit_data else []
        
        if recent_events:
            for event in reversed(recent_events):
                timestamp = event.get('timestamp', '')[:19]
                action = event.get('action', '')
                actor = event.get('actor', 'Unknown')
                st.write(f"• **{timestamp}** - {actor} performed {action}")
        else:
            st.info("No recent activity")
            
    except Exception as e:
        st.error(f"Error loading system data: {e}")

def show_user_management(user):
    """User management interface"""
    st.subheader("👥 User Management")
    
    try:
        users_data = read_json("data/users.json")
        
        # Display current users
        st.markdown("#### Current Users")
        for i, user_info in enumerate(users_data):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"📧 {user_info.get('email', 'Unknown')}")
            with col2:
                st.write(f"👤 {user_info.get('role', 'Unknown')}")
            with col3:
                if st.button("🗑️", key=f"delete_user_{i}", help="Delete user"):
                    if st.session_state.get(f"confirm_delete_user_{i}", False):
                        users_data.pop(i)
                        write_json("data/users.json", users_data)
                        st.success("User deleted!")
                        st.rerun()
                    else:
                        st.session_state[f"confirm_delete_user_{i}"] = True
                        st.warning("Click again to confirm")
        
        # Add new user
        st.markdown("#### Add New User")
        with st.form("add_user_form"):
            new_email = st.text_input("Email:")
            new_password = st.text_input("Password:", type="password")
            new_role = st.selectbox("Role:", ["Student", "Teacher"])
            
            if st.form_submit_button("Add User"):
                if new_email and new_password:
                    new_user = {
                        "email": new_email,
                        "password": new_password,
                        "role": new_role
                    }
                    users_data.append(new_user)
                    write_json("data/users.json", users_data)
                    st.success("User added successfully!")
                    st.rerun()
                else:
                    st.error("Please fill all fields")
                    
    except Exception as e:
        st.error(f"Error managing users: {e}")

def show_settings_management(user):
    """Settings management interface"""
    st.subheader("⚙️ System Settings")
    
    try:
        settings = read_json("data/settings.json")
        
        # Notification settings
        st.markdown("#### 📧 Notification Settings")
        email_enabled = st.checkbox(
            "Email notifications enabled",
            value=settings.get("notifications", {}).get("email", {}).get("enabled", False)
        )
        
        telegram_enabled = st.checkbox(
            "Telegram notifications enabled",
            value=settings.get("notifications", {}).get("telegram", {}).get("enabled", False)
        )
        
        # Media settings
        st.markdown("#### 📸 Media Settings")
        thumbnails_enabled = st.checkbox(
            "Thumbnail generation enabled",
            value=settings.get("thumbnails", {}).get("enabled", True)
        )
        
        approval_required = st.checkbox(
            "Media approval required",
            value=settings.get("media_approval", {}).get("enabled", True)
        )
        
        # Save settings
        if st.button("💾 Save Settings"):
            settings["notifications"]["email"]["enabled"] = email_enabled
            settings["notifications"]["telegram"]["enabled"] = telegram_enabled
            settings["thumbnails"]["enabled"] = thumbnails_enabled
            settings["media_approval"]["enabled"] = approval_required
            
            write_json("data/settings.json", settings)
            st.success("Settings saved successfully!")
            
    except Exception as e:
        st.error(f"Error managing settings: {e}")
