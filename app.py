# This is the main file - run this with: streamlit run app.py
import streamlit as st
from auth.authentication import login_view, do_logout
from features import rooms, faculty, media

st.set_page_config(page_title="Department Portal", layout="centered")

# Initialize session state - DO NOT MODIFY
if "user" not in st.session_state:
    st.session_state.user = None

def show_app():
    # Sidebar - user info and navigation
    st.sidebar.write(f"**Logged in as:** {st.session_state.user['email']}")
    st.sidebar.write(f"**Role:** {st.session_state.user['role']}")
    
    # Logout button
    if st.sidebar.button("🚪 Logout"):
        do_logout()
        st.stop()

    # Main navigation menu
    st.sidebar.markdown("---")
    choice = st.sidebar.radio(
        "**📋 Select Feature:**",
        ["🏠 Room Booking", "👨‍🏫 Faculty Availability", "📸 Department Media"],
        index=0
    )

    # Route to appropriate feature
    if choice == "🏠 Room Booking":
        rooms.main(st.session_state.user)
    elif choice == "👨‍🏫 Faculty Availability":
        faculty.main()
    elif choice == "📸 Department Media":
        media.main(st.session_state.user)

def main():
    # Main app logic - shows login or app based on session state
    if st.session_state.user is None:
        login_view()  # Show login page
    else:
        show_app()    # Show main application

if __name__ == "__main__":
    main()
