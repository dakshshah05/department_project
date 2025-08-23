# Room booking functionality with audit trail and notifications
import streamlit as st
from datetime import datetime, date, timedelta, time
from utils.io import read_json, write_json
from utils.audit import log_audit_event, get_booking_history
from utils.notify import send_booking_confirmation, send_booking_cancelled

ROOM_FILE = "data/rooms.json"
WEEK_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def _load_rooms():
    """Load room data from JSON file"""
    try:
        return read_json(ROOM_FILE)
    except FileNotFoundError:
        st.error("❌ Room data file not found at data/rooms.json.")
        return {}

def _save_rooms(data: dict):
    """Save room data to JSON file"""
    write_json(ROOM_FILE, data)

def _get_day_name(selected_date):
    """Convert date to day name"""
    return selected_date.strftime("%A")

def _slot_to_time_range(slot_str, base_date):
    """Convert time slot string to datetime range"""
    try:
        start_str, end_str = slot_str.split('-')
        is_pm = 'PM' in end_str
        
        start_str = start_str.replace('AM', '').replace('PM', '')
        end_str = end_str.replace('AM', '').replace('PM', '')
        
        start_hour = int(start_str)
        end_hour = int(end_str)
        
        if is_pm and start_hour != 12:
            start_hour += 12
        if is_pm and end_hour != 12:
            end_hour += 12
        elif not is_pm and start_hour == 12:
            start_hour = 0
        elif not is_pm and end_hour == 12:
            end_hour = 0
            
        start_time = datetime.combine(base_date, time(start_hour, 0))
        end_time = datetime.combine(base_date, time(end_hour, 0))
        
        return start_time, end_time
    except Exception as e:
        st.error(f"Error parsing time slot '{slot_str}': {e}")
        return None, None

def _reset_expired_bookings(rooms_data, current_datetime):
    """Reset bookings that have expired"""
    current_day = current_datetime.strftime('%A')
    current_date = current_datetime.date()
    
    updated = False
    expired_slots = []
    
    for room_name, schedule in rooms_data.items():
        if current_day not in schedule:
            continue
            
        day_slots = schedule[current_day]
        
        for slot, is_booked in day_slots.items():
            if is_booked:
                start_time, end_time = _slot_to_time_range(slot, current_date)
                
                if start_time and end_time and current_datetime >= end_time:
                    day_slots[slot] = False
                    updated = True
                    expired_slots.append(f"{room_name} - {slot}")
                    
                    # Log auto-expiry
                    log_audit_event(
                        "SYSTEM",
                        "AUTO_EXPIRE",
                        "ROOM_BOOKING",
                        f"{room_name}|{current_day}|{slot}",
                        {"expired_at": current_datetime.isoformat()}
                    )
    
    return updated, expired_slots

def main(user: dict):
    """Main room booking interface with audit trail"""
    st.header("🏠 Room Booking System (Enhanced)")
    st.markdown("---")

    # Load room data
    data = _load_rooms()
    if not data:
        st.warning("⚠️ No room data available.")
        return

    # Auto-reset expired bookings
    current_time = datetime.now()
    reset_occurred, expired_list = _reset_expired_bookings(data, current_time)
    
    if reset_occurred:
        _save_rooms(data)
        if expired_list:
            st.success("🔄 **Auto-Reset:** The following expired bookings have been freed:")
            for expired in expired_list:
                st.success(f"✅ {expired}")

    # Initialize session state for date navigation
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = date.today()

    # Room selection
    room_names = list(data.keys())
    room = st.selectbox(
        "🚪 Select Room:", 
        room_names,
        help="Choose a room to view/book its schedule"
    )

    # Date selection
    st.subheader("📅 Select Date")
    
    today = date.today()
    min_date = today
    max_date = today + timedelta(days=60)
    
    selected_date = st.date_input(
        "📅 Choose a date to view/book:",
        value=st.session_state.selected_date,
        min_value=min_date,
        max_value=max_date,
        help="Select any date to see room availability",
        key="date_picker"
    )
    
    st.session_state.selected_date = selected_date
    day_name = _get_day_name(selected_date)
    
    if day_name not in data[room]:
        st.warning(f"⚠️ No timetable available for {day_name}s.")
        return

    # Display selected date info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**📅 Date:** {selected_date.strftime('%B %d, %Y')}")
    with col2:
        st.info(f"**🗓️ Day:** {day_name}")
    with col3:
        if selected_date == today:
            st.success("**📍 Today**")
            st.caption(f"🕒 Current: {current_time.strftime('%I:%M %p')}")
        else:
            days_ahead = (selected_date - today).days
            st.info(f"**⏩ {days_ahead} day{'s' if days_ahead > 1 else ''} ahead**")

    # Display timetable
    st.subheader(f"🏠 {room} — {selected_date.strftime('%A, %B %d')}")
    
    timeslots = data[room][day_name]
    free_slots = [t for t, booked in timeslots.items() if not booked]
    booked_slots = [t for t, booked in timeslots.items() if booked]

    # Display slots
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**🟢 Available Slots:**")
        if free_slots:
            for t in free_slots:
                if selected_date == today:
                    start_time, end_time = _slot_to_time_range(t, selected_date)
                    if start_time and end_time:
                        if start_time <= current_time < end_time:
                            st.success(f"✅ {t} 🔥 (CURRENT)")
                        else:
                            st.success(f"✅ {t}")
                    else:
                        st.success(f"✅ {t}")
                else:
                    st.success(f"✅ {t}")
        else:
            st.info("No available slots")

    with col2:
        st.write("**🔴 Booked Slots:**")
        if booked_slots:
            for t in booked_slots:
                if selected_date == today:
                    start_time, end_time = _slot_to_time_range(t, selected_date)
                    if start_time and end_time:
                        if current_time < start_time:
                            time_until = start_time - current_time
                            hours, remainder = divmod(time_until.seconds, 3600)
                            minutes, _ = divmod(remainder, 60)
                            st.error(f"❌ {t} (starts in {hours}h {minutes}m)")
                        elif start_time <= current_time < end_time:
                            time_left = end_time - current_time
                            hours, remainder = divmod(time_left.seconds, 3600)
                            minutes, _ = divmod(remainder, 60)
                            st.error(f"❌ {t} ⏰ (ends in {hours}h {minutes}m)")
                        else:
                            st.error(f"❌ {t} (expired - will reset)")
                    else:
                        st.error(f"❌ {t}")
                else:
                    st.error(f"❌ {t}")
        else:
            st.info("No booked slots")

    # Summary
    total_slots = len(timeslots)
    st.metric(
        label="📊 Availability Summary", 
        value=f"{len(free_slots)}/{total_slots} slots free",
        delta=f"{len(booked_slots)} booked"
    )

    # Teacher booking functionality
    if user["role"].lower() == "teacher":
        st.markdown("---")
        st.subheader("🔒 Book a Slot (Teacher Only)")
        
        st.info(f"🎯 **Booking for:** {selected_date.strftime('%A, %B %d, %Y')}")
        
        if selected_date == today:
            st.warning("⚠️ **Auto-Reset:** Bookings automatically become free when their time expires")
        
        if free_slots:
            # Booking form
            with st.form("booking_form"):
                slot_to_book = st.selectbox(
                    "⏰ Choose an available time slot:", 
                    free_slots,
                    help="Select a time slot to book"
                )
                
                booking_title = st.text_input(
                    "📝 Meeting/Class Title:",
                    placeholder="e.g., CS101 Lecture, Team Meeting, etc.",
                    help="Brief description of your booking"
                )
                
                booking_purpose = st.selectbox(
                    "🎯 Purpose:",
                    ["Class/Lecture", "Meeting", "Seminar", "Workshop", "Exam", "Other"],
                    help="What will you use the room for?"
                )
                
                expected_attendees = st.number_input(
                    "👥 Expected Attendees:",
                    min_value=1,
                    max_value=100,
                    value=20,
                    help="Approximate number of people"
                )
                
                notify_me = st.checkbox(
                    "📧 Send me confirmation and reminders",
                    value=True,
                    help="Get email/telegram notifications"
                )
                
                submitted = st.form_submit_button("📝 Book Slot", type="primary")
                
                if submitted:
                    # Double-check slot is still free
                    if not data[room][day_name].get(slot_to_book, True):
                        # Book the slot
                        data[room][day_name][slot_to_book] = True
                        _save_rooms(data)
                        
                        # Log booking
                        booking_details = {
                            "title": booking_title or "Untitled Booking",
                            "purpose": booking_purpose,
                            "attendees": expected_attendees,
                            "notify": notify_me
                        }
                        
                        entity_id = f"{room}|{day_name}|{slot_to_book}"
                        log_audit_event(
                            user["email"],
                            "BOOK",
                            "ROOM_BOOKING",
                            entity_id,
                            booking_details
                        )
                        
                        # Send notification
                        if notify_me:
                            send_booking_confirmation(
                                user["email"],
                                room,
                                selected_date.strftime('%A, %B %d, %Y'),
                                slot_to_book
                            )
                        
                        st.success(f"✅ **Booking Confirmed!**")
                        st.success(f"🏠 **Room:** {room}")
                        st.success(f"📅 **Date:** {selected_date.strftime('%A, %B %d, %Y')}")
                        st.success(f"⏰ **Time:** {slot_to_book}")
                        st.success(f"📝 **Title:** {booking_title or 'Untitled Booking'}")
                        
                        if selected_date == today:
                            start_time, end_time = _slot_to_time_range(slot_to_book, selected_date)
                            if end_time:
                                st.info(f"🔄 **Auto-Reset:** This booking will automatically free at {end_time.strftime('%I:%M %p')}")
                        
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Slot was just booked by someone else. Please refresh.")
                        st.rerun()
        else:
            st.warning("⚠️ No available slots for this date.")
    
    # Booking history for the selected room/day
    with st.expander(f"📊 **Booking History:** {room} - {day_name}", expanded=False):
        st.write("**Recent booking activity for this room and day:**")
        
        # Get history for all slots of this room/day
        all_history = []
        for slot in timeslots.keys():
            slot_history = get_booking_history(room, day_name, slot)
            all_history.extend(slot_history)
        
        # Sort by timestamp
        all_history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        if all_history:
            for event in all_history[:10]:  # Show last 10 events
                timestamp = event.get('timestamp', '')
                action = event.get('action', '')
                actor = event.get('actor', 'Unknown')
                details = event.get('details', {})
                entity_id = event.get('entity_id', '')
                
                try:
                    _, _, slot = entity_id.split('|')
                    if timestamp:
                        dt = datetime.fromisoformat(timestamp.replace('Z', ''))
                        time_str = dt.strftime('%m/%d %I:%M %p')
                    else:
                        time_str = 'Unknown time'
                    
                    if action == "BOOK":
                        title = details.get('title', 'Untitled')
                        st.success(f"📝 **{time_str}** - {actor} booked {slot} - \"{title}\"")
                    elif action == "AUTO_EXPIRE":
                        st.info(f"🔄 **{time_str}** - System auto-expired {slot}")
                    elif action == "CANCEL":
                        st.warning(f"❌ **{time_str}** - {actor} cancelled {slot}")
                except:
                    st.text(f"• {timestamp} - {action} by {actor}")
        else:
            st.info("No booking history available for this room and day.")

    # Quick date navigation
    st.markdown("---")
    st.subheader("🔄 Quick Date Navigation")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("⏪ Yesterday", help="Go to yesterday"):
            if selected_date > today:
                st.session_state.selected_date = selected_date - timedelta(days=1)
                st.rerun()
    
    with col2:
        if st.button("📍 Today", help="Go to today"):
            st.session_state.selected_date = today
            st.rerun()
    
    with col3:
        if st.button("⏩ Tomorrow", help="Go to tomorrow"):
            st.session_state.selected_date = selected_date + timedelta(days=1)
            st.rerun()
    
    with col4:
        if st.button("📅 Next Week", help="Go to same day next week"):
            st.session_state.selected_date = selected_date + timedelta(days=7)
            st.rerun()

    # Manual refresh
    if st.button("🔄 **Refresh & Check for Expired Bookings**"):
        st.rerun()
