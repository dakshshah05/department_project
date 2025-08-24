# Main entry point with embedded CSS for university logo
import streamlit as st
import base64
from pathlib import Path
from auth.authentication import login_view, do_logout
from features import rooms, faculty, media, finder

st.set_page_config(page_title="Department Portal", layout="centered")

def add_logo_and_styling():
    """Add university logo and custom styling directly in app.py"""
    
    # Read logo file and convert to base64
    try:
        logo_path = Path("university_logo.png")
        if logo_path.exists():
            logo_data = base64.b64encode(logo_path.read_bytes()).decode()
            logo_html = f'<img class="fixed-logo" src="data:image/png;base64,{logo_data}" alt="University Logo">'
        else:
            # Fallback text logo if image not found
            logo_html = '<div class="fixed-logo-text">🏛️ Your University</div>'
    except Exception as e:
        logo_html = '<div class="fixed-logo-text">🏛️ Your University</div>'
    
    # CSS + Logo HTML embedded in the same file
    st.markdown(f"""
    <style>
        /* University logo styling */
        .fixed-logo {{
            position: fixed;
            top: auto;
            right: 15px;
            height: 60px;  /* Adjust this for bigger/smaller logo */
            width: auto;
            z-index: 9999;
            border-radius: 5px;  /* Optional: rounded corners */
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);  /* Optional: subtle shadow */
        }}
        
        /* Fallback text logo styling */
        .fixed-logo-text {{
            position: fixed;
            top: 15px;
            left: 15px;
            font-size: 28px;
            font-weight: bold;
            color: #1f77b4;
            z-index: 9999;
            background: white;
            padding: 10px 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        /* Adjust main content to avoid overlap with logo */
        .main .block-container {{
            padding-top: 150px;  /* Increase if logo is bigger */
        }}
        
        /* Adjust sidebar to avoid overlap with logo */
        [data-testid="stSidebar"] {{
            margin-top: 140px;  /* Increase if logo is bigger */
        }}
        
        /* Optional: Hide Streamlit's default header space */
        .css-18e3th9 {{
            padding-top: 0rem;
        }}
        
        /* Optional: Custom styling for the sidebar */
        [data-testid="stSidebar"] > div:first-child {{
            background-color: #f8f9fa;
        }}
    </style>
    {logo_html}
    """, unsafe_allow_html=True)

# Add logo and styling at the very beginning
add_logo_and_styling()

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None

def show_app():
    st.sidebar.write(f"**Logged in as:** {st.session_state.user['email']}")
    st.sidebar.write(f"**Role:** {st.session_state.user['role']}")
    
    if st.sidebar.button("🚪 Logout"):
        do_logout()
        st.stop()

    st.sidebar.markdown("---")
    choice = st.sidebar.radio(
        "**📋 Select Feature:**",
        [
            "🏠 Room Booking", 
            "👨‍🏫 Faculty Availability", 
            "🔍 Free Room Finder",
            "📸 Media Center"
        ],
        index=0
    )

    if choice == "🏠 Room Booking":
        rooms.main(st.session_state.user)
    elif choice == "👨‍🏫 Faculty Availability":
        faculty.main()
    elif choice == "🔍 Free Room Finder":
        finder.main(st.session_state.user)
    elif choice == "📸 Media Center":
        media.main(st.session_state.user)

def main():
    if st.session_state.user is None:
        login_view()
    else:
        show_app()

if __name__ == "__main__":
    main()
