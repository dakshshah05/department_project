# Faculty availability display with calendar date selection - View only for all users
import streamlit as st
from datetime import datetime, date, timedelta
from utils.io import read_json

FACULTY_FILE = "data/faculty.json"  # TO MODIFY FACULTY: Edit this file

WEEK_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def _get_day_name(selected_date):
    """Convert date to day name (Monday, Tuesday, etc.)"""
    return selected_date.strftime("%A")

def _ordered_days(days_dict: dict):
    """Return days sorted by week order"""
    existing = list(days_dict.keys())
    ordered = [d for d in WEEK_ORDER if d in existing]
    # Include any extra custom day labels at the end
    for d in existing:
        if d not in ordered:
            ordered.append(d)
    return ordered

def main():
    """
    Faculty availability viewer with calendar date selection
    TO ADD FACULTY: Edit data/faculty.json
    TO ADD DAYS: Add day keys to faculty objects
    TO ADD TIME SLOTS: Add time keys inside day objects
    """
    st.header("👨‍🏫 Faculty Availability (Calendar-Based)")
    st.markdown("---")

    # Load faculty data
    try:
        data = read_json(FACULTY_FILE)
    except FileNotFoundError:
        st.error("❌ Faculty data file not found at data/faculty.json.")
        st.info("**File should contain:** Faculty objects with days → time slots (true=busy, false=free)")
        return

    # Initialize session state for date navigation
    if "faculty_selected_date" not in st.session_state:
        st.session_state.faculty_selected_date = date.today()

    # Faculty selection
    names = list(data.keys())
    faculty = st.selectbox(
        "👤 Select Faculty:", 
        names,
        help="Choose a faculty member to view their schedule"
    )

    # Date selection with calendar
    st.subheader("📅 Select Date")
    
    # Default to today, but allow past and future dates
    today = date.today()
    min_date = today - timedelta(days=30)  # Allow 30 days back
    max_date = today + timedelta(days=60)  # Allow 60 days forward
    
    selected_date = st.date_input(
        "📅 Choose a date to check availability:",
        value=st.session_state.faculty_selected_date,
        min_value=min_date,
        max_value=max_date,
        help="Select any date to see faculty availability for that day",
        key="faculty_date_picker"
    )
    
    # Update session state when date changes
    st.session_state.faculty_selected_date = selected_date

    # Convert selected date to day name
    day_name = _get_day_name(selected_date)
    
    # Check if the day exists in our timetable
    if day_name not in data[faculty]:
        st.warning(f"⚠️ No schedule available for {day_name}s. Available days: {', '.join(data[faculty].keys())}")
        return

    # Display selected date info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**📅 Date:** {selected_date.strftime('%B %d, %Y')}")
    with col2:
        st.info(f"**🗓️ Day:** {day_name}")
    with col3:
        # Show if it's today, past, or future
        if selected_date == today:
            st.success("**📍 Today**")
        elif selected_date < today:
            days_ago = (today - selected_date).days
            st.warning(f"**⏪ {days_ago} day{'s' if days_ago > 1 else ''} ago**")
        else:
            days_ahead = (selected_date - today).days
            st.info(f"**⏩ {days_ahead} day{'s' if days_ahead > 1 else ''} ahead**")

    # Display availability for chosen date
    st.subheader(f"👨‍🏫 {faculty} — {selected_date.strftime('%A, %B %d')}")
    
    times = data[faculty][day_name]
    free_slots = [t for t, busy in times.items() if not busy]
    busy_slots = [t for t, busy in times.items() if busy]

    # Display in columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**🟢 Available Times:**")
        if free_slots:
            for t in free_slots:
                st.success(f"✅ {t}")
        else:
            st.info("No free times")

    with col2:
        st.write("**🔴 Busy Times:**")
        if busy_slots:
            for t in busy_slots:
                st.error(f"❌ {t}")
        else:
            st.info("No busy times")

    # Summary
    total_slots = len(times)
    st.metric(
        label="📊 Availability Summary", 
        value=f"{len(free_slots)}/{total_slots} slots free",
        delta=f"{len(busy_slots)} busy"
    )

    # Quick date navigation using session state
    st.markdown("---")
    st.subheader("🔄 Quick Date Navigation")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("⏪ Yesterday", key="faculty_yesterday"):
            st.session_state.faculty_selected_date = selected_date - timedelta(days=1)
            st.rerun()
    
    with col2:
        if st.button("📍 Today", key="faculty_today"):
            st.session_state.faculty_selected_date = today
            st.rerun()
    
    with col3:
        if st.button("⏩ Tomorrow", key="faculty_tomorrow"):
            st.session_state.faculty_selected_date = selected_date + timedelta(days=1)
            st.rerun()
    
    with col4:
        if st.button("📅 Next Week", key="faculty_next_week"):
            st.session_state.faculty_selected_date = selected_date + timedelta(days=7)
            st.rerun()

    # Weekly overview for the selected faculty
    with st.expander(f"🔍 **Weekly Schedule:** {faculty}", expanded=False):
        st.write("**📅 Current Week Schedule:**")
        
        # Calculate week start (Monday)
        week_start = selected_date - timedelta(days=selected_date.weekday())
        
        for i, day_key in enumerate(WEEK_ORDER[:7]):  # Mon-Sun
            if day_key in data[faculty]:
                check_date = week_start + timedelta(days=i)
                day_times = data[faculty][day_key]
                free_count = sum(1 for busy in day_times.values() if not busy)
                total_count = len(day_times)
                
                # Highlight selected date
                if check_date == selected_date:
                    st.success(f"👉 **{day_key} ({check_date.strftime('%m/%d')})** - {free_count}/{total_count} free ⭐")
                else:
                    st.write(f"📅 **{day_key} ({check_date.strftime('%m/%d')})** - {free_count}/{total_count} free")

    # Show all faculty summary for selected date
    with st.expander("📊 **All Faculty Summary**", expanded=False):
        st.write(f"**Overview for {selected_date.strftime('%A, %B %d')}:**")
        for name in names:
            if day_name in data[name]:
                faculty_day = data[name][day_name]
                free_count = sum(1 for busy in faculty_day.values() if not busy)
                busy_count = sum(1 for busy in faculty_day.values() if busy)
                
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    if name == faculty:
                        st.success(f"👉 **{name}** (selected)")
                    else:
                        st.write(f"👨‍🏫 **{name}**")
                with col2:
                    st.metric("Free", free_count)
                with col3:
                    st.metric("Busy", busy_count)
