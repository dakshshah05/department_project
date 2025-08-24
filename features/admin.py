# Simplified admin panel without analytics features
import streamlit as st
from utils.io import read_json, write_json
from utils.audit import get_audit_history

def main(user):
    """Simplified admin panel interface"""
    st.header("⚙️ Admin Panel")
    st.markdown("---")
    
    if user["role"].lower() != "teacher":
        st.error("❌ Access denied. Admin panel is for teachers only.")
        return
    
    # Simplified admin tabs (NO ANALYTICS)
    tab1, tab2, tab3 = st.tabs(["📊 System Overview", "👥 User Management", "⚙️ Settings"])
    
    with tab1:
        show_simple_overview()
    
    with tab2:
        show_user_management(user)
    
    with tab3:
        show_settings_management(user)

def show_simple_overview():
    """Display simple system overview without charts"""
    st.subheader("📊 System Overview")
    
    try:
        # Load data
        rooms_data = read_json("data/rooms.json")
        faculty_data = read_json("data/faculty.json")
        users_data = read_json("data/users.json")
        audit_data = read_json("data/audit_log.json")
        
        # Simple metrics without charts
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🚪 Total Rooms", len(rooms_data))
        with col2:
            st.metric("👨‍🏫 Faculty Members", len(faculty_data))
        with col3:
            st.metric("👥 Total Users", len(users_data))
        with col4:
            st.metric("📋 Total Events", len(audit_data))
        
        # Simple room status
        st.markdown("#### 🚪 Room Status Summary")
        for room, schedule in rooms_data.items():
            total_slots = 0
            booked_slots = 0
            
            for day, slots in schedule.items():
                total_slots += len(slots)
                booked_slots += sum(slots.values())
            
            utilization = round((booked_slots / total_slots) * 100, 1) if total_slots > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**{room}**")
            with col2:
                st.write(f"{booked_slots}/{total_slots} slots")
            with col3:
                if utilization > 70:
                    st.error(f"{utilization}% (High)")
                elif utilization > 40:
                    st.warning(f"{utilization}% (Medium)")
                else:
                    st.success(f"{utilization}% (Low)")
        
        # Recent activity (text only)
        st.markdown("#### 📈 Recent Activity")
        recent_events = audit_data[-10:] if audit_data else []
        
        if recent_events:
            for event in reversed(recent_events):
                timestamp = event.get('timestamp', '')[:19]
                action = event.get('action', '')
                actor = event.get('actor', 'Unknown')
                
                if action == "BOOK":
                    st.success(f"📝 **{timestamp}** - {actor} booked a room")
                elif action == "CANCEL":
                    st.warning(f"❌ **{timestamp}** - {actor} cancelled a booking")
                elif action == "AUTO_EXPIRE":
                    st.info(f"🔄 **{timestamp}** - System auto-expired a booking")
                else:
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
        
        # Display current users in a simple table
        st.markdown("#### Current Users")
        
        # Create a simple table
        user_table_data = []
        for user_info in users_data:
            user_table_data.append({
                "Email": user_info.get('email', 'Unknown'),
                "Role": user_info.get('role', 'Unknown')
            })
        
        if user_table_data:
            st.table(user_table_data)
        
        # Simple user stats
        teachers = sum(1 for u in users_data if u.get('role', '').lower() == 'teacher')
        students = sum(1 for u in users_data if u.get('role', '').lower() == 'student')
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("👨‍🏫 Teachers", teachers)
        with col2:
            st.metric("👨‍🎓 Students", students)
        with col3:
            st.metric("📊 Total", len(users_data))
        
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
        
        # Simple settings without complex analytics
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
        
        # Saturday settings
        st.markdown("#### 📅 Schedule Settings")
        saturday_working = st.checkbox(
            "Saturdays are working days",
            value=settings.get("saturday_schedule", {}).get("working_saturdays", True)
        )
        
        exclude_third_saturday = st.checkbox(
            "Exclude 3rd Saturday of month",
            value=settings.get("saturday_schedule", {}).get("exclude_third_saturday", True)
        )
        
        # Save settings
        if st.button("💾 Save Settings"):
            settings["notifications"]["email"]["enabled"] = email_enabled
            settings["notifications"]["telegram"]["enabled"] = telegram_enabled
            settings["thumbnails"]["enabled"] = thumbnails_enabled
            settings["media_approval"]["enabled"] = approval_required
            settings["saturday_schedule"]["working_saturdays"] = saturday_working
            settings["saturday_schedule"]["exclude_third_saturday"] = exclude_third_saturday
            
            write_json("data/settings.json", settings)
            st.success("Settings saved successfully!")
            
    except Exception as e:
        st.error(f"Error managing settings: {e}")

def show_data_export():
    """Simple data export without analytics"""
    st.markdown("#### 📤 Data Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Export Room Data"):
            try:
                rooms_data = read_json("data/rooms.json")
                st.success("Room data exported successfully!")
                st.json(rooms_data)
            except Exception as e:
                st.error(f"Export failed: {e}")
    
    with col2:
        if st.button("👥 Export User Data"):
            try:
                users_data = read_json("data/users.json")
                # Remove passwords from export for security
                safe_users = []
                for user in users_data:
                    safe_user = {"email": user.get("email"), "role": user.get("role")}
                    safe_users.append(safe_user)
                
                st.success("User data exported successfully!")
                st.json(safe_users)
            except Exception as e:
                st.error(f"Export failed: {e}")
