# Handles user login and logout with default Streamlit theme
import streamlit as st
from utils.io import read_json

USERS_FILE = "data/users.json"

def login_view():
    """
    Displays login form with default Streamlit styling
    """
    # University header with logo
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Add university name and logo in login page
        try:
            st.image("christ_logo.png", width=200)
        except:
            st.markdown("# 🏛️ Christ University")
        
        st.markdown("# Christ University")
        st.markdown("## Department Portal")
    
    st.markdown("---")
    
    # Demo credentials info box
    st.info("""
    **📋 Demo Credentials:**
    
    **Teachers:**
    • daksh.kumar@bcah.christuniversity.in / daksh123
    • syeda.shariya@bcah.christuniversity.in / shariya123
    
    **Students:**
    • harsh.behal@bcah.christuniversity.in / harsh123
    • deevyanshu.sahu@bcah.christuniversity.in / deevyanshu123  
    • bhavishya.bodwani@bcah.christuniversity.in / bhavishya123
    """)

    with st.form("login_form"):
        email = st.text_input(
            "📧 University Email", 
            placeholder="name@bcah.christuniversity.in",
            help="Enter your Christ University email ID"
        )
        password = st.text_input(
            "🔐 Password", 
            type="password",
            placeholder="Enter your password",
            help="Enter your password"
        )
        role = st.radio(
            "👤 Login as:", 
            ["Student", "Teacher"], 
            horizontal=True,
            help="Select your role"
        )
        submitted = st.form_submit_button("🚀 Login", use_container_width=True)

    if submitted:
        try:
            users = read_json(USERS_FILE)
        except FileNotFoundError:
            st.error("❌ Users file not found. Please ensure data/users.json exists.")
            return

        for u in users:
            if (
                u.get("email") == email
                and u.get("password") == password
                and u.get("role", "").lower() == role.lower()
            ):
                st.session_state.user = {"email": email, "role": role}
                st.success("✅ Login successful! Loading application...")
                st.rerun()
                return

        st.error("❌ Invalid credentials. Please check your email, password, and role.")

def do_logout():
    """
    Clears user session and returns to login page
    """
    st.session_state.user = None
    st.success("👋 Logged out successfully!")
    st.rerun()
