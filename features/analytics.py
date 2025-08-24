# Analytics dashboard with room utilization and faculty workload
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, date, timedelta
from utils.io import read_json
from utils.analytics_utils import calculate_room_utilization, calculate_faculty_workload
import json

def main(user):
    """Analytics dashboard with charts and reports"""
    st.header("📊 Analytics Dashboard")
    st.markdown("---")
    
    # Load data
    try:
        rooms_data = read_json("data/rooms.json")
        faculty_data = read_json("data/faculty.json")
        audit_data = read_json("data/audit_log.json")
        booking_history = read_json("data/booking_history.json")
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return
    
    # Tabs for different analytics
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏠 Room Utilization", 
        "👨‍🏫 Faculty Workload", 
        "📈 Booking Statistics", 
        "📊 Reports"
    ])
    
    with tab1:
        show_room_utilization(rooms_data, audit_data)
    
    with tab2:
        show_faculty_workload(faculty_data, audit_data)
    
    with tab3:
        show_booking_statistics(audit_data, booking_history)
    
    with tab4:
        show_reports_section(rooms_data, faculty_data, audit_data, user)

def show_room_utilization(rooms_data, audit_data):
    """Display room utilization charts"""
    st.subheader("🏠 Room Utilization Analysis")
    
    # Calculate utilization data
    utilization_data = []
    for room, schedule in rooms_data.items():
        total_slots = 0
        booked_slots = 0
        
        for day, slots in schedule.items():
            total_slots += len(slots)
            booked_slots += sum(slots.values())
        
        utilization_rate = (booked_slots / total_slots * 100) if total_slots > 0 else 0
        
        utilization_data.append({
            'Room': room,
            'Total Slots': total_slots,
            'Booked Slots': booked_slots,
            'Available Slots': total_slots - booked_slots,
            'Utilization Rate (%)': round(utilization_rate, 1)
        })
    
    if utilization_data:
        df = pd.DataFrame(utilization_data)
        
        # Room utilization bar chart
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Room Utilization Rates")
            fig_bar = px.bar(
                df, 
                x='Room', 
                y='Utilization Rate (%)',
                title='Room Utilization Percentage',
                color='Utilization Rate (%)',
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col2:
            st.markdown("#### 🥧 Overall Room Usage")
            total_booked = df['Booked Slots'].sum()
            total_available = df['Available Slots'].sum()
            
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Booked', 'Available'],
                values=[total_booked, total_available],
                hole=.3
            )])
            fig_pie.update_layout(title="Overall Room Availability")
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Detailed table
        st.markdown("#### 📋 Detailed Room Statistics")
        st.dataframe(df, use_container_width=True)
        
        # Peak hours analysis
        st.markdown("#### ⏰ Peak Hours Analysis")
        peak_hours_data = analyze_peak_hours(rooms_data)
        if peak_hours_data:
            fig_heatmap = px.imshow(
                peak_hours_data,
                labels=dict(x="Time Slot", y="Day", color="Bookings"),
                title="Room Booking Heatmap (Peak Hours)"
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)

def show_faculty_workload(faculty_data, audit_data):
    """Display faculty workload analytics"""
    st.subheader("👨‍🏫 Faculty Workload Analysis")
    
    workload_data = []
    for faculty, schedule in faculty_data.items():
        total_slots = 0
        busy_slots = 0
        
        for day, slots in schedule.items():
            total_slots += len(slots)
            busy_slots += sum(slots.values())
        
        workload_rate = (busy_slots / total_slots * 100) if total_slots > 0 else 0
        
        workload_data.append({
            'Faculty': faculty,
            'Total Hours': total_slots,
            'Teaching Hours': busy_slots,
            'Free Hours': total_slots - busy_slots,
            'Workload (%)': round(workload_rate, 1)
        })
    
    if workload_data:
        df = pd.DataFrame(workload_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Faculty Workload Distribution")
            fig_bar = px.bar(
                df, 
                x='Faculty', 
                y='Workload (%)',
                title='Faculty Workload Percentage',
                color='Workload (%)',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col2:
            st.markdown("#### 📈 Teaching vs Free Hours")
            fig_scatter = px.scatter(
                df, 
                x='Teaching Hours', 
                y='Free Hours',
                size='Total Hours',
                hover_name='Faculty',
                title='Teaching Hours vs Free Hours'
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        # Faculty workload table
        st.markdown("#### 📋 Faculty Workload Details")
        st.dataframe(df, use_container_width=True)

def show_booking_statistics(audit_data, booking_history):
    """Display booking statistics and trends"""
    st.subheader("📈 Booking Statistics & Trends")
    
    if not audit_data:
        st.info("No booking data available for analysis.")
        return
    
    # Filter booking events
    booking_events = [
        event for event in audit_data 
        if event.get('action') in ['BOOK', 'CANCEL', 'AUTO_EXPIRE']
    ]
    
    if booking_events:
        # Convert to DataFrame for analysis
        df = pd.DataFrame(booking_events)
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Bookings over time
            daily_bookings = df[df['action'] == 'BOOK'].groupby('date').size()
            
            if not daily_bookings.empty:
                fig_line = px.line(
                    x=daily_bookings.index, 
                    y=daily_bookings.values,
                    title='Daily Booking Trends',
                    labels={'x': 'Date', 'y': 'Number of Bookings'}
                )
                st.plotly_chart(fig_line, use_container_width=True)
        
        with col2:
            # Action distribution
            action_counts = df['action'].value_counts()
            
            fig_pie = px.pie(
                values=action_counts.values,
                names=action_counts.index,
                title='Booking Actions Distribution'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Weekly summary
        st.markdown("#### 📅 Weekly Booking Summary")
        if len(df) > 0:
            df['weekday'] = pd.to_datetime(df['timestamp']).dt.day_name()
            weekly_stats = df[df['action'] == 'BOOK'].groupby('weekday').size().reindex([
                'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
            ], fill_value=0)
            
            fig_bar = px.bar(
                x=weekly_stats.index,
                y=weekly_stats.values,
                title='Bookings by Day of Week',
                labels={'x': 'Day', 'y': 'Number of Bookings'}
            )
            st.plotly_chart(fig_bar, use_container_width=True)

def show_reports_section(rooms_data, faculty_data, audit_data, user):
    """Display reports and export functionality"""
    st.subheader("📊 Reports & Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📈 Quick Reports")
        
        if st.button("📊 Generate Room Utilization Report"):
            generate_room_report(rooms_data)
        
        if st.button("👨‍🏫 Generate Faculty Workload Report"):
            generate_faculty_report(faculty_data)
        
        if st.button("📅 Generate Booking History Report"):
            generate_booking_report(audit_data)
    
    with col2:
        st.markdown("#### 📤 Export Options")
        
        # Date range selection
        date_from = st.date_input("From Date", value=date.today() - timedelta(days=30))
        date_to = st.date_input("To Date", value=date.today())
        
        if st.button("📄 Export to PDF"):
            st.info("PDF export functionality will be implemented soon.")
        
        if st.button("📊 Export to Excel"):
            generate_excel_export(rooms_data, faculty_data, audit_data, date_from, date_to)

def analyze_peak_hours(rooms_data):
    """Analyze peak booking hours across all rooms"""
    try:
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        time_slots = list(list(rooms_data.values())[0]['Monday'].keys())
        
        heatmap_data = []
        for day in days:
            day_bookings = []
            for slot in time_slots:
                total_booked = sum(
                    1 for room_schedule in rooms_data.values() 
                    if day in room_schedule and room_schedule[day].get(slot, False)
                )
                day_bookings.append(total_booked)
            heatmap_data.append(day_bookings)
        
        return heatmap_data
    except Exception as e:
        st.error(f"Error analyzing peak hours: {e}")
        return None

def generate_room_report(rooms_data):
    """Generate room utilization report"""
    st.success("📊 Room Utilization Report Generated")
    
    # Create summary
    summary_data = []
    for room, schedule in rooms_data.items():
        total = sum(len(slots) for slots in schedule.values())
        booked = sum(sum(slots.values()) for slots in schedule.values())
        summary_data.append({
            'Room': room,
            'Total Slots': total,
            'Booked': booked,
            'Utilization %': round((booked/total)*100, 1) if total > 0 else 0
        })
    
    df = pd.DataFrame(summary_data)
    st.dataframe(df, use_container_width=True)

def generate_faculty_report(faculty_data):
    """Generate faculty workload report"""
    st.success("👨‍🏫 Faculty Workload Report Generated")
    
    summary_data = []
    for faculty, schedule in faculty_data.items():
        total = sum(len(slots) for slots in schedule.values())
        busy = sum(sum(slots.values()) for slots in schedule.values())
        summary_data.append({
            'Faculty': faculty,
            'Total Hours': total,
            'Teaching Hours': busy,
            'Workload %': round((busy/total)*100, 1) if total > 0 else 0
        })
    
    df = pd.DataFrame(summary_data)
    st.dataframe(df, use_container_width=True)

def generate_booking_report(audit_data):
    """Generate booking history report"""
    st.success("📅 Booking History Report Generated")
    
    if audit_data:
        booking_events = [
            event for event in audit_data[-50:]  # Last 50 events
            if event.get('action') in ['BOOK', 'CANCEL']
        ]
        
        if booking_events:
            df = pd.DataFrame(booking_events)
            st.dataframe(df[['timestamp', 'actor', 'action', 'entity_id']], use_container_width=True)
        else:
            st.info("No booking events found in recent history.")
    else:
        st.info("No audit data available.")

def generate_excel_export(rooms_data, faculty_data, audit_data, date_from, date_to):
    """Generate Excel export (placeholder)"""
    st.success("📊 Excel export prepared for download")
    st.info("Feature will be enhanced to provide actual Excel file download.")
    
    # In a real implementation, you would use pandas.to_excel()
    # and streamlit download_button
