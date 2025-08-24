# Main entry point without analytics dashboard
import streamlit as st
import base64
from pathlib import Path
from auth.authentication import login_view, do_logout
from features import rooms, faculty, media, finder, admin, notifications

st.set_page_config(page_title="Christ University - Department Portal", layout="centered")

def add_christ_logo_and_styling():
    """Add Christ University logo with minimal styling"""
    try:
        logo_path = Path("university_logo.png")
        if logo_path.exists():
            logo_data = base64.b64encode(logo_path.read_bytes()).decode()
            logo_html = f'<img class="fixed-logo" src="data:image/png;base64,{logo_data}" alt="Christ University Logo">'
        else:
            logo_html = '<div class="fixed-logo-text">Christ University</div>'
    except:
        logo_html = '<div class="fixed-logo-text">Christ University</div>'
    
    st.markdown(f"""
    <style>
        /* Logo Styling */
        .fixed-logo {{
            position: fixed;
            top: auto;
            right: 15px;
            height: 60px;
            width: auto;
            z-index: 9999;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        /* Layout Adjustments */
        .main .block-container {{
            padding-top: 130px;
        }}
        
        [data-testid="stSidebar"] {{
            margin-top: 120px;
        }}
        
        /* Clean styling for buttons */
        .stButton > button {{
            background-color: #1f77b4;
            color: white;
            border: none;
            border-radius: 5px;
        }}
        
        .stButton > button:hover {{
            background-color: #1565c0;
        }}
    </style>
    {logo_html}
    """, unsafe_allow_html=True)

# Add logo and styling
add_christ_logo_and_styling()

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None

def show_app():
    """Main application interface without analytics"""
    st.sidebar.write(f"**Logged in as:** {st.session_state.user['email']}")
    st.sidebar.write(f"**Role:** {st.session_state.user['role']}")
    
    if st.sidebar.button("🚪 Logout"):
        do_logout()
        st.stop()

    st.sidebar.markdown("---")
    
    # Simplified navigation menu (NO ANALYTICS)
    base_options = [
        "🚪 Room Booking", 
        "👨‍🏫 Faculty Availability", 
        "🔍 Free Room Finder",
        "📸 Media Center",
        "🔔 Notifications"
    ]
    
    # Add admin options for teachers
    if st.session_state.user['role'].lower() == 'teacher':
        base_options.append("⚙️ Admin Panel")
    
    choice = st.sidebar.radio("**📋 Select Feature:**", base_options, index=0)

    # Route to selected feature (NO ANALYTICS ROUTING)
    if choice == "🚪 Room Booking":
        rooms.main(st.session_state.user)
    elif choice == "👨‍🏫 Faculty Availability":
        faculty.main()
    elif choice == "🔍 Free Room Finder":
        finder.main(st.session_state.user)
    elif choice == "📸 Media Center":
        media.main(st.session_state.user)
    elif choice == "🔔 Notifications":
        notifications.main(st.session_state.user)
    elif choice == "⚙️ Admin Panel":
        admin.main(st.session_state.user)

def main():
    if st.session_state.user is None:
        login_view()
    else:
        show_app()

if __name__ == "__main__":
    main()
