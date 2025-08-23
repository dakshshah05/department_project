# Main entry point with enhanced navigation
import streamlit as st
from auth.authentication import login_view, do_logout
from features import rooms, faculty, media, finder

st.set_page_config(page_title="Department Portal", layout="wide")

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
