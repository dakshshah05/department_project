# Faculty availability display - View only for all users
import streamlit as st
from utils.io import read_json

FACULTY_FILE = "data/faculty.json"  # TO MODIFY FACULTY: Edit this file

def main():
    """
    Faculty availability viewer
    TO ADD FACULTY: Edit data/faculty.json
    """
    st.header("👨‍🏫 Faculty Availability")
    st.markdown("---")

    # Load faculty data
    try:
        data = read_json(FACULTY_FILE)
    except FileNotFoundError:
        st.error("❌ Faculty data file not found at data/faculty.json.")
        st.info("**File should contain:** Faculty objects with time slots (true=busy, false=free)")
        return

    # Faculty selection
    names = list(data.keys())
    choice = st.selectbox(
        "👤 Select Faculty:", 
        ["📋 Show All Faculty"] + names, 
        index=0,
        help="Choose a specific faculty member or view all"
    )

    if choice == "📋 Show All Faculty":
        # Show all faculty in a grid
        st.subheader("📊 All Faculty Availability")
        
        for name in names:
            with st.expander(f"👨‍🏫 {name}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**🟢 Free Times:**")
                    free_found = False
                    for slot, busy in data[name].items():
                        if not busy:
                            st.success(f"✅ {slot}")
                            free_found = True
                    if not free_found:
                        st.warning("No free slots")
                
                with col2:
                    st.write("**🔴 Busy Times:**")
                    busy_found = False
                    for slot, busy in data[name].items():
                        if busy:
                            st.error(f"❌ {slot}")
                            busy_found = True
                    if not busy_found:
                        st.info("All slots free")
    else:
        # Show specific faculty
        st.subheader(f"📅 Schedule for {choice}")
        
        col1, col2 = st.columns(2)
        
        free_count = 0
        busy_count = 0
        
        with col1:
            st.write("**🟢 Free Times:**")
            for slot, busy in data[choice].items():
                if not busy:
                    st.success(f"✅ {slot}")
                    free_count += 1
        
        with col2:
            st.write("**🔴 Busy Times:**")
            for slot, busy in data[choice].items():
                if busy:
                    st.error(f"❌ {slot}")
                    busy_count += 1
        
        # Summary
        st.info(f"📊 **Summary:** {free_count} free, {busy_count} busy slots")
