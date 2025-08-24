# Enhanced room booking with cancellations, conflict detection, and waitlist
import streamlit as st
from datetime import datetime, date, timedelta, time
from utils.io import read_json, write_json, append_json_array
from utils.audit import log_audit_event, get_booking_history
from utils.notify import send_booking_confirmation, send_booking_cancelled
from utils.scheduler_utils import get_saturday_schedule, is_working_saturday

ROOM_FILE = "data/rooms.json"
BOOKING_HISTORY_FILE = "data/booking_history.json"
WAITLIST_FILE = "data/waitlist.json"
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
    """Convert date to day name with Saturday handling"""
    day_name = selected_date.strftime("%A")
    
    # Handle Saturday schedule (except 3rd Saturday)
    if day_name == "Saturday":
        if not is_working_saturday(selected_date):
            return None  # 3rd Saturday - holiday
    
    return day_name

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
        return None, None

def _check_booking_conflicts(room, day_name, slot, user_email):
    """Check for booking conflicts"""
    conflicts = []
    
    # Check faculty conflicts
    try:
        faculty_data = read_json("data/faculty.json")
        
        # Find if user is a faculty member
        user_faculty = None
        for faculty_name, schedule in faculty_data.items():
            if user_email.split('@')[0].replace('.', ' ').title() in faculty_name:
                user_faculty = faculty_name
                break
        
        if user_faculty and day_name in faculty_data[user_faculty]:
            if faculty_data[user_faculty][day_name].get(slot, False):
                conflicts.append(f"⚠️ You have a conflicting commitment at {slot} on {day_name}")
    except:
        pass
    
    return conflicts

def _add_to_waitlist(room, day_name, slot, user_email, user_role):
    """Add user to waitlist for a booked slot"""
    try:
        waitlist = read_json(WAITLIST_FILE)
    except:
        waitlist = []
    
    waitlist_entry = {
        "id": f"waitlist_{datetime.now().timestamp()}",
        "room": room,
        "day": day_name,
        "slot": slot,
        "user_email": user_email,
        "user_role": user_role,
        "timestamp": datetime.now().isoformat(),
        "status": "waiting"
    }
    
    waitlist.append(waitlist_entry)
    write_json(WAITLIST_FILE, waitlist)
    return waitlist_entry["id"]

def _process_waitlist(room, day_name, slot):
    """Process waitlist when a slot becomes available"""
    try:
        waitlist = read_json(WAITLIST_FILE)
        
        # Find waiting users for this slot
        waiting_users = [
            w for w in waitlist 
            if w["room"] == room and w["day"] == day_name and w["slot"] == slot and w["status"] == "waiting"
        ]
        
        if waiting_users:
            # Sort by timestamp (first come, first served)
            waiting_users.sort(key=lambda x: x["timestamp"])
            
            # Notify first user in queue
            first_user = waiting_users[0]
            
            # Update waitlist status
            for w in waitlist:
                if w["id"] == first_user["id"]:
                    w["status"] = "notified"
                    w["notified_at"] = datetime.now().isoformat()
            
            write_json(WAITLIST_FILE, waitlist)
            
            # Send notification
            send_waitlist_notification(first_user)
            
            return first_user["user_email"]
        
    except Exception as e:
        st.error(f"Error processing waitlist: {e}")
    
    return None

def _cancel_booking(room, day_name, slot, user_email, reason=""):
    """Cancel a booking and update records"""
    try:
        # Load room data
        data = _load_rooms()
        
        if room in data and day_name in data[room] and slot in data[room][day_name]:
            if data[room][day_name][slot]:  # If slot is booked
                # Free the slot
                data[room][day_name][slot] = False
                _save_rooms(data)
                
                # Log cancellation
                entity_id = f"{room}|{day_name}|{slot}"
                log_audit_event(
                    user_email,
                    "CANCEL",
                    "ROOM_BOOKING",
                    entity_id,
                    {"reason": reason, "cancelled_at": datetime.now().isoformat()}
                )
                
                # Update booking history
                update_booking_history(user_email, room, day_name, slot, "CANCELLED")
                
                # Send notification
                send_booking_cancelled(user_email, room, f"{day_name}", slot, reason)
                
                # Process waitlist
                notified_user = _process_waitlist(room, day_name, slot)
                
                return True, notified_user
            else:
                return False, "Slot is not currently booked"
        else:
            return False, "Invalid booking details"
            
    except Exception as e:
        return False, f"Error cancelling booking: {e}"

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
                    
                    # Process waitlist for expired slot
                    _process_waitlist(room_name, current_day, slot)
    
    return updated, expired_slots

def update_booking_history(user_email, room, day, slot, action):
    """Update personal booking history"""
    try:
        history = read_json(BOOKING_HISTORY_FILE)
    except:
        history = []
    
    history_entry = {
        "user_email": user_email,
        "room": room,
        "day": day,
        "slot": slot,
        "action": action,
        "timestamp": datetime.now().isoformat()
    }
    
    history.append(history_entry)
    write_json(BOOKING_HISTORY_FILE, history)

def show_personal_booking_history(user_email):
    """Display user's personal booking history"""
    try:
        history = read_json(BOOKING_HISTORY_FILE)
        user_history = [h for h in history if h["user_email"] == user_email]
        
        if user_history:
            st.subheader("📋 Your Booking History")
            
            # Sort by timestamp (newest first)
            user_history.sort(key=lambda x: x["timestamp"], reverse=True)
            
            for i, booking in enumerate(user_history[:10]):  # Show last 10 bookings
                action_icon = {
                    'BOOKED': '✅',
                    'CANCELLED': '❌',
                    'EXPIRED': '⏰'
                }.get(booking['action'], '📋')
                
                timestamp = datetime.fromisoformat(booking['timestamp']).strftime("%m/%d %I:%M %p")
                
                st.write(f"{action_icon} **{booking['room']}** - {booking['day']} {booking['slot']} - {booking['action']} on {timestamp}")
        else:
            st.info("📭 No booking history found.")
            
    except Exception as e:
        st.error(f"Error loading booking history: {e}")

def show_waitlist_status(user_email):
    """Display user's waitlist status"""
    try:
        waitlist = read_json(WAITLIST_FILE)
        user_waitlist = [w for w in waitlist if w["user_email"] == user_email and w["status"] == "waiting"]
        
        if user_waitlist:
            st.subheader("⏳ Your Waitlist Status")
            
            for item in user_waitlist:
                st.info(f"🕐 Waiting for **{item['room']}** - {item['day']} {item['slot']}")
                if st.button(f"❌ Cancel Waitlist", key=f"cancel_waitlist_{item['id']}"):
                    cancel_waitlist_entry(item['id'])
                    st.success("Waitlist entry cancelled!")
                    st.rerun()
    except:
        pass

def cancel_waitlist_entry(waitlist_id):
    """Cancel a waitlist entry"""
    try:
        waitlist = read_json(WAITLIST_FILE)
        waitlist = [w for w in waitlist if w["id"] != waitlist_id]
        write_json(WAITLIST_FILE, waitlist)
    except:
        pass

def send_waitlist_notification(waitlist_entry):
    """Send notification to waitlist user"""
    # This would integrate with the notification system
    pass

def main(user: dict):
    """Enhanced room booking interface"""
    st.header("🚪 Room Booking System")
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

    # Initialize session state
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = date.today()

    # Show personal history and waitlist
    if user["role"].lower() == "teacher":
        with st.expander("📋 **My Bookings & Waitlist**", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                show_personal_booking_history(user["email"])
            with col2:
                show_waitlist_status(user["email"])

    # Room selection
    room_names = list(data.keys())
    room = st.selectbox(
        "🚪 Select Room:", 
        room_names,
        help="Choose a room to view/book its schedule"
    )

    # Date selection with Saturday handling
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
    
    # Check for 3rd Saturday
    if day_name is None:
        st.warning("🎉 **Holiday:** Third Saturday of the month - No classes scheduled!")
        st.info("💡 All Saturdays are working days except the 3rd Saturday of each month.")
        return
    
    if day_name not in data[room]:
        st.warning(f"⚠️ No timetable available for {day_name}s.")
        return

    # Display selected date info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**📅 Date:** {selected_date.strftime('%B %d, %Y')}")
    with col2:
        st.info(f"**🗓️ Day:** {day_name}")
        if day_name == "Saturday":
            st.caption("✅ Working Saturday")
    with col3:
        if selected_date == today:
            st.success("**📍 Today**")
            st.caption(f"🕒 Current: {current_time.strftime('%I:%M %p')}")
        else:
            days_ahead = (selected_date - today).days
            st.info(f"**⏩ {days_ahead} day{'s' if days_ahead > 1 else ''} ahead**")

    # Display timetable
    st.subheader(f"🚪 {room} — {selected_date.strftime('%A, %B %d')}")
    
    timeslots = data[room][day_name]
    free_slots = [t for t, booked in timeslots.items() if not booked]
    booked_slots = [t for t, booked in timeslots.items() if booked]

    # Display slots with enhanced info
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
        st.subheader("🔒 Booking Options (Teacher Only)")
        
        st.info(f"🎯 **Booking for:** {selected_date.strftime('%A, %B %d, %Y')}")
        
        # Booking and Cancellation tabs
        tab1, tab2 = st.tabs(["📝 Book Slot", "❌ Cancel Booking"])
        
        with tab1:
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
                        # Check for conflicts
                        conflicts = _check_booking_conflicts(room, day_name, slot_to_book, user["email"])
                        
                        if conflicts:
                            for conflict in conflicts:
                                st.warning(conflict)
                            
                            if st.button("⚠️ Book Anyway"):
                                # Proceed with booking despite conflicts
                                book_slot_logic(data, room, day_name, slot_to_book, user, booking_title, booking_purpose, expected_attendees, notify_me)
                        else:
                            # No conflicts, proceed with booking
                            book_slot_logic(data, room, day_name, slot_to_book, user, booking_title, booking_purpose, expected_attendees, notify_me)
            else:
                st.warning("⚠️ No available slots for this date.")
                
                # Waitlist option
                if booked_slots:
                    st.markdown("#### ⏳ Join Waitlist")
                    st.info("Join the waitlist to be notified when a slot becomes available.")
                    
                    waitlist_slot = st.selectbox(
                        "⏰ Select slot for waitlist:",
                        booked_slots,
                        help="Choose a booked slot to join its waitlist"
                    )
                    
                    if st.button("⏳ Join Waitlist"):
                        waitlist_id = _add_to_waitlist(room, day_name, waitlist_slot, user["email"], user["role"])
                        st.success(f"✅ Added to waitlist for {room} - {day_name} {waitlist_slot}")
                        st.info("You'll be notified when this slot becomes available.")
        
        with tab2:
            # Cancellation form
            st.write("**Cancel Your Existing Bookings:**")
            
            # Get user's current bookings
            try:
                history = read_json(BOOKING_HISTORY_FILE)
                user_active_bookings = [
                    h for h in history 
                    if h["user_email"] == user["email"] and h["action"] == "BOOKED"
                    and h["room"] == room and h["day"] == day_name
                ]
                
                # Filter only currently booked slots
                current_bookings = [
                    b for b in user_active_bookings 
                    if data[room][day_name].get(b["slot"], False)
                ]
                
                if current_bookings:
                    with st.form("cancellation_form"):
                        booking_to_cancel = st.selectbox(
                            "📋 Select booking to cancel:",
                            [f"{b['slot']}" for b in current_bookings],
                            help="Choose one of your active bookings to cancel"
                        )
                        
                        cancellation_reason = st.text_area(
                            "📝 Reason for cancellation (optional):",
                            placeholder="e.g., Meeting postponed, room requirements changed, etc.",
                            help="Brief explanation for the cancellation"
                        )
                        
                        cancel_submitted = st.form_submit_button("❌ Cancel Booking", type="secondary")
                        
                        if cancel_submitted:
                            success, message = _cancel_booking(room, day_name, booking_to_cancel, user["email"], cancellation_reason)
                            
                            if success:
                                st.success(f"✅ Successfully cancelled: {room} - {day_name} {booking_to_cancel}")
                                if isinstance(message, str) and message:  # If a user was notified from waitlist
                                    st.info(f"📧 Waitlist user {message} has been notified!")
                                st.rerun()
                            else:
                                st.error(f"❌ Cancellation failed: {message}")
                else:
                    st.info("📭 You have no active bookings for this room and date.")
                    
            except Exception as e:
                st.error(f"Error loading your bookings: {e}")
    
    else:
        st.info("👁️ **Student Access:** View-only mode")

    # Enhanced booking history with search - FIXED: Pass data parameter
    with st.expander(f"📊 **Booking History:** {room} - {day_name}", expanded=False):
        show_enhanced_booking_history(room, day_name, user, data)  # ✅ Fixed: Added data parameter

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

def book_slot_logic(data, room, day_name, slot_to_book, user, booking_title, booking_purpose, expected_attendees, notify_me):
    """Handle the actual booking logic"""
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
        
        # Update booking history
        update_booking_history(user["email"], room, day_name, slot_to_book, "BOOKED")
        
        # Send notification
        if notify_me:
            send_booking_confirmation(
                user["email"],
                room,
                f"{day_name}",
                slot_to_book
            )
        
        st.success(f"✅ **Booking Confirmed!**")
        st.success(f"🚪 **Room:** {room}")
        st.success(f"📅 **Date:** {day_name}")
        st.success(f"⏰ **Time:** {slot_to_book}")
        st.success(f"📝 **Title:** {booking_title or 'Untitled Booking'}")
        
        st.balloons()
        st.rerun()
    else:
        st.error("❌ Slot was just booked by someone else. Please refresh.")
        st.rerun()

def show_enhanced_booking_history(room, day_name, user, rooms_data):  # ✅ Fixed: Added rooms_data parameter
    """Show enhanced booking history with search and filters"""
    st.write("**Recent booking activity for this room and day:**")
    
    # Search and filter options
    col1, col2 = st.columns(2)
    with col1:
        search_user = st.text_input("🔍 Search by user email:", placeholder="user@domain.com")
    with col2:
        action_filter = st.selectbox("📋 Filter by action:", ["All", "BOOK", "CANCEL", "AUTO_EXPIRE"])
    
    # Get history for all slots of this room/day - FIXED: Use rooms_data parameter
    all_history = []
    if room in rooms_data and day_name in rooms_data[room]:  # ✅ Fixed: Use rooms_data instead of data
        for slot in rooms_data[room][day_name].keys():  # ✅ Fixed: Use rooms_data instead of data
            slot_history = get_booking_history(room, day_name, slot)
            all_history.extend(slot_history)
    
    # Apply filters
    if search_user:
        all_history = [h for h in all_history if search_user.lower() in h.get('actor', '').lower()]
    
    if action_filter != "All":
        all_history = [h for h in all_history if h.get('action') == action_filter]
    
    # Sort by timestamp
    all_history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    if all_history:
        for event in all_history[:15]:  # Show last 15 events
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
                    reason = details.get('reason', 'No reason provided')
                    st.warning(f"❌ **{time_str}** - {actor} cancelled {slot} - Reason: {reason}")
            except:
                st.text(f"• {timestamp} - {action} by {actor}")
    else:
        st.info("No booking history found matching your criteria.")
