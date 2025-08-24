# Handles user login and logout - uses local JSON file for credentials
import streamlit as st
from utils.io import read_json

USERS_FILE = "data/users.json"  # Path to user credentials

def login_view():
    """
    Displays login form and handles authentication
    TO ADD NEW USERS: Edit data/users.json file
    """
    st.title("🏛️ Department Portal Login")
    st.markdown("---")
    st.info("**Demo Credentials:**\n- daksh.kumar@bcah.christuniversity.in / daksh123 (teacher)\n- syeda.shariya@bcah.christuniversity.in / shariya123 (Teacher)")

    with st.form("login_form"):
        email = st.text_input(
            "📧 Gmail ID", 
            placeholder="example@gmail.com",
            help="Enter your registered Gmail ID"
        )
        password = st.text_input(
            "🔐 Password", 
            type="password",
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
        # Load users from JSON file
        try:
            users = read_json(USERS_FILE)
        except FileNotFoundError:
            st.error("❌ Users file not found. Please ensure data/users.json exists.")
            st.info("**File should contain:** List of user objects with email, password, and role")
            return

        # Check credentials
        for u in users:
            if (
                u.get("email") == email
                and u.get("password") == password
                and u.get("role", "").lower() == role.lower()
            ):
                # Login successful
                st.session_state.user = {"email": email, "role": role}
                st.success("✅ Login successful! Loading application...")
                st.rerun()
                return

        # Login failed
        st.error("❌ Invalid credentials. Please check your email, password, and role.")

def do_logout():
    """
    Clears user session and returns to login page
    """
    st.session_state.user = None
    st.success("👋 Logged out successfully!")
    st.rerun()
