# Free room finder across all rooms and time ranges
import streamlit as st
from datetime import datetime, date, timedelta
from utils.io import read_json
from utils.audit import log_audit_event

ROOM_FILE = "data/rooms.json"
WEEK_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def _get_day_name(selected_date):
    """Convert date to day name"""
    return selected_date.strftime("%A")

def _parse_time_slot(slot_str):
    """Parse time slot to get start hour for sorting"""
    try:
        start_str = slot_str.split('-')[0]
        start_hour = int(start_str.replace('AM', '').replace('PM', ''))
        if 'PM' in slot_str and start_hour != 12:
            start_hour += 12
        elif 'AM' in slot_str and start_hour == 12:
            start_hour = 0
        return start_hour
    except:
        return 0

def find_free_rooms(rooms_data, search_date, time_slots):
    """Find rooms that are free for all specified time slots"""
    day_name = _get_day_name(search_date)
    free_rooms = []
    
    for room_name, schedule in rooms_data.items():
        if day_name not in schedule:
            continue
        
        room_slots = schedule[day_name]
        
        # Check if all requested slots are free
        all_free = True
        available_slots = []
        
        for slot in time_slots:
            if slot in room_slots and not room_slots[slot]:
                available_slots.append(slot)
            else:
                all_free = False
                break
        
        if all_free and available_slots:
            free_rooms.append({
                "room": room_name,
                "available_slots": available_slots
            })
    
    return free_rooms

def main(user):
    """Free room finder interface"""
    st.header("🔍 Free Room Finder")
    st.markdown("---")
    st.info("Find available rooms across all locations for your desired date and time slots.")
    
    # Load room data
    try:
        rooms_data = read_json(ROOM_FILE)
    except:
        st.error("❌ Could not load room data.")
        return
    
    if not rooms_data:
        st.warning("⚠️ No room data available.")
        return
    
    # Search parameters
    col1, col2 = st.columns(2)
    
    with col1:
        search_date = st.date_input(
            "📅 Select Date:",
            value=date.today(),
            min_value=date.today(),
            max_value=date.today() + timedelta(days=60),
            help="Choose the date you need a room"
        )
    
    with col2:
        # Get all available time slots from first room
        sample_room = list(rooms_data.keys())[0]
        day_name = _get_day_name(search_date)
        
        if day_name in rooms_data[sample_room]:
            all_slots = sorted(
                rooms_data[sample_room][day_name].keys(), 
                key=_parse_time_slot
            )
            
            selected_slots = st.multiselect(
                "⏰ Select Time Slots:",
                all_slots,
                help="Choose one or more time slots you need"
            )
        else:
            st.warning(f"No schedule available for {day_name}s")
            return
    
    # Search button
    if st.button("🔍 Search Free Rooms", type="primary"):
        if not selected_slots:
            st.warning("⚠️ Please select at least one time slot.")
            return
        
        # Log search activity
        log_audit_event(
            user["email"], 
            "SEARCH", 
            "FREE_ROOMS", 
            f"{search_date}|{','.join(selected_slots)}", 
            {"slots_count": len(selected_slots)}
        )
        
        # Perform search
        free_rooms = find_free_rooms(rooms_data, search_date, selected_slots)
        
        st.markdown("---")
        
        if free_rooms:
            st.success(f"✅ Found {len(free_rooms)} available rooms for {search_date.strftime('%A, %B %d, %Y')}")
            
            # Display results
            for i, result in enumerate(free_rooms, 1):
                with st.expander(f"🏠 {result['room']} - {len(result['available_slots'])} slots available", expanded=i <= 3):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write("**Available Time Slots:**")
                        for slot in result['available_slots']:
                            st.success(f"✅ {slot}")
                    
                    with col2:
                        if user["role"].lower() == "teacher":
                            st.write("**Quick Actions:**")
                            if st.button(f"📝 Book All Slots", key=f"book_all_{result['room']}"):
                                # Redirect to room booking with pre-selection
                                st.session_state.quick_book = {
                                    "room": result['room'],
                                    "date": search_date,
                                    "slots": result['available_slots']
                                }
                                st.success("✅ Redirecting to booking page...")
                                st.info("💡 Use the Room Booking page to complete your reservation")
        else:
            st.error("❌ No rooms available for the selected date and time slots")
            st.info("💡 **Suggestions:**")
            st.info("• Try different time slots")
            st.info("• Check a different date")
            st.info("• Consider splitting your booking across multiple rooms")
        
        # Alternative suggestions
        if not free_rooms:
            st.markdown("---")
            st.subheader("📋 Alternative Options")
            
            # Find rooms with partial availability
            partial_rooms = []
            day_name = _get_day_name(search_date)
            
            for room_name, schedule in rooms_data.items():
                if day_name not in schedule:
                    continue
                
                room_slots = schedule[day_name]
                available_slots = [slot for slot in selected_slots if slot in room_slots and not room_slots[slot]]
                
                if 0 < len(available_slots) < len(selected_slots):
                    partial_rooms.append({
                        "room": room_name,
                        "available": available_slots,
                        "unavailable": [slot for slot in selected_slots if slot not in available_slots or room_slots.get(slot, True)]
                    })
            
            if partial_rooms:
                st.write("**🔶 Partially Available Rooms:**")
                for room in partial_rooms:
                    with st.expander(f"🏠 {room['room']} - {len(room['available'])}/{len(selected_slots)} slots free"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**✅ Available:**")
                            for slot in room['available']:
                                st.success(f"✅ {slot}")
                        with col2:
                            st.write("**❌ Unavailable:**")
                            for slot in room['unavailable']:
                                st.error(f"❌ {slot}")
    
    # Usage tips
    with st.expander("💡 **How to use Free Room Finder**", expanded=False):
        st.markdown("""
        **🎯 Purpose:**
        - Find rooms available for specific dates and times
        - Compare availability across all rooms at once
        - Plan meetings and classes efficiently
        
        **📋 How to use:**
        1. **Select Date:** Choose when you need the room
        2. **Select Time Slots:** Pick one or more consecutive time periods
        3. **Search:** Click search to see all available rooms
        4. **Book:** Use quick actions or go to Room Booking page
        
        **💡 Tips:**
        - Select multiple time slots for longer meetings
        - Use this before checking individual room schedules
        - Try different dates if no rooms are available
        - Teachers can quick-book directly from results
        """)
    
    # Recent searches (if we want to add this feature)
    if user["role"].lower() == "teacher":
        st.markdown("---")
        with st.expander("📊 **My Recent Searches**", expanded=False):
            st.info("Feature coming soon: View your recent room searches and save favorite search patterns")
