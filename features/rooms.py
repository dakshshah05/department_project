# Room booking functionality - Teachers can book, Students view only
import streamlit as st
from utils.io import read_json, write_json

ROOM_FILE = "data/rooms.json"  # TO MODIFY ROOMS: Edit this file

def _load_rooms():
    """Load room data from JSON file"""
    try:
        return read_json(ROOM_FILE)
    except FileNotFoundError:
        st.error("❌ Room data file not found at data/rooms.json.")
        st.info("**File should contain:** Room objects with time slots (false=free, true=booked)")
        return {}

def _save_rooms(data: dict):
    """Save room data to JSON file"""
    write_json(ROOM_FILE, data)

def main(user: dict):
    """
    Main room booking interface
    - Students: View only
    - Teachers: View + Book slots
    TO ADD ROOMS: Edit data/rooms.json
    """
    st.header("🏠 Room Booking System")
    st.markdown("---")

    # Load room data
    data = _load_rooms()
    if not data:
        st.warning("⚠️ No room data available.")
        return

    # Room selection
    room_names = list(data.keys())
    room = st.selectbox(
        "🚪 Select Room:", 
        room_names,
        help="Choose a room to view its schedule"
    )

    # Display room schedule
    st.subheader(f"📅 Schedule for {room}")
    
    # Create columns for better layout
    col1, col2 = st.columns(2)
    
    free_count = 0
    booked_count = 0
    
    with col1:
        st.write("**🟢 Free Slots:**")
        for slot, booked in data[room].items():
            if not booked:
                st.success(f"✅ {slot}")
                free_count += 1
    
    with col2:
        st.write("**🔴 Booked Slots:**")
        for slot, booked in data[room].items():
            if booked:
                st.error(f"❌ {slot}")
                booked_count += 1

    # Summary
    st.info(f"📊 **Summary:** {free_count} free, {booked_count} booked slots")

    # Teacher booking functionality
    if user["role"].lower() == "teacher":
        st.markdown("---")
        st.subheader("🔒 Book a Slot (Teacher Only)")
        
        free_slots = [s for s, b in data[room].items() if not b]
        if not free_slots:
            st.warning("⚠️ No free slots available to book.")
            return

        book_slot = st.selectbox(
            "⏰ Choose a free slot:", 
            free_slots, 
            key=f"book_{room}",
            help="Select a time slot to book"
        )
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("📝 Book Slot", type="primary"):
                # Double-check slot is still free
                if not data[room].get(book_slot, True):
                    data[room][book_slot] = True
                    _save_rooms(data)
                    st.success(f"✅ Successfully booked: **{room}** → **{book_slot}**")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Slot was just booked by someone else. Refreshing...")
                    st.rerun()
        
        with col2:
            st.caption("💡 Tip: Booking will be saved immediately and visible to all users")
    else:
        st.info("👁️ **Student Access:** View-only mode")
