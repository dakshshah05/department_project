# Analytics utility functions for room utilization and faculty workload calculations
from datetime import datetime, timedelta
import json

def calculate_room_utilization(rooms_data):
    """
    Calculate room utilization percentage for each room
    Returns dict with room names as keys and utilization percentage as values
    """
    utilization = {}
    
    for room, schedule in rooms_data.items():
        total_slots = 0
        booked_slots = 0
        
        for day, slots in schedule.items():
            total_slots += len(slots)
            booked_slots += sum(1 for slot, booked in slots.items() if booked)
        
        # Calculate utilization percentage
        utilization_rate = (booked_slots / total_slots) * 100 if total_slots > 0 else 0
        utilization[room] = round(utilization_rate, 2)
    
    return utilization

def calculate_faculty_workload(faculty_data):
    """
    Calculate faculty workload percentage for each faculty member
    Returns dict with faculty names as keys and workload percentage as values
    """
    workload = {}
    
    for faculty, schedule in faculty_data.items():
        total_slots = 0
        busy_slots = 0
        
        for day, slots in schedule.items():
            total_slots += len(slots)
            busy_slots += sum(1 for slot, busy in slots.items() if busy)
        
        # Calculate workload percentage
        workload_rate = (busy_slots / total_slots) * 100 if total_slots > 0 else 0
        workload[faculty] = round(workload_rate, 2)
    
    return workload

def get_peak_hours_analysis(rooms_data):
    """
    Analyze peak booking hours across all rooms
    Returns dict with time slots and their booking frequency
    """
    try:
        slot_usage = {}
        
        # Get all unique time slots
        all_slots = set()
        for room_schedule in rooms_data.values():
            for day_schedule in room_schedule.values():
                all_slots.update(day_schedule.keys())
        
        # Count bookings per slot across all rooms and days
        for slot in all_slots:
            total_bookings = 0
            total_possible = 0
            
            for room_schedule in rooms_data.values():
                for day_schedule in room_schedule.values():
                    if slot in day_schedule:
                        total_possible += 1
                        if day_schedule[slot]:
                            total_bookings += 1
            
            if total_possible > 0:
                usage_rate = (total_bookings / total_possible) * 100
                slot_usage[slot] = round(usage_rate, 2)
        
        return slot_usage
    except Exception as e:
        print(f"Error in peak hours analysis: {e}")
        return {}

def get_daily_utilization_trends(rooms_data):
    """
    Get utilization trends by day of week
    Returns dict with days as keys and utilization rates as values
    """
    try:
        daily_trends = {}
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for day in days:
            total_slots = 0
            booked_slots = 0
            
            for room_schedule in rooms_data.values():
                if day in room_schedule:
                    day_slots = room_schedule[day]
                    total_slots += len(day_slots)
                    booked_slots += sum(1 for booked in day_slots.values() if booked)
            
            if total_slots > 0:
                utilization_rate = (booked_slots / total_slots) * 100
                daily_trends[day] = round(utilization_rate, 2)
            else:
                daily_trends[day] = 0
        
        return daily_trends
    except Exception as e:
        print(f"Error in daily trends analysis: {e}")
        return {}

def calculate_room_statistics(rooms_data):
    """
    Calculate comprehensive room statistics
    Returns dict with various statistics
    """
    try:
        stats = {
            "total_rooms": len(rooms_data),
            "total_slots": 0,
            "booked_slots": 0,
            "free_slots": 0,
            "utilization_rate": 0,
            "most_used_room": None,
            "least_used_room": None
        }
        
        room_utilization = calculate_room_utilization(rooms_data)
        
        if room_utilization:
            # Find most and least used rooms
            stats["most_used_room"] = max(room_utilization, key=room_utilization.get)
            stats["least_used_room"] = min(room_utilization, key=room_utilization.get)
        
        # Calculate totals
        for room_schedule in rooms_data.values():
            for day_schedule in room_schedule.values():
                stats["total_slots"] += len(day_schedule)
                stats["booked_slots"] += sum(1 for booked in day_schedule.values() if booked)
        
        stats["free_slots"] = stats["total_slots"] - stats["booked_slots"]
        
        if stats["total_slots"] > 0:
            stats["utilization_rate"] = round((stats["booked_slots"] / stats["total_slots"]) * 100, 2)
        
        return stats
    except Exception as e:
        print(f"Error calculating room statistics: {e}")
        return {}

def calculate_faculty_statistics(faculty_data):
    """
    Calculate comprehensive faculty statistics
    Returns dict with various statistics
    """
    try:
        stats = {
            "total_faculty": len(faculty_data),
            "total_hours": 0,
            "busy_hours": 0,
            "free_hours": 0,
            "average_workload": 0,
            "busiest_faculty": None,
            "most_available_faculty": None
        }
        
        faculty_workload = calculate_faculty_workload(faculty_data)
        
        if faculty_workload:
            # Find busiest and most available faculty
            stats["busiest_faculty"] = max(faculty_workload, key=faculty_workload.get)
            stats["most_available_faculty"] = min(faculty_workload, key=faculty_workload.get)
            
            # Calculate average workload
            stats["average_workload"] = round(sum(faculty_workload.values()) / len(faculty_workload), 2)
        
        # Calculate totals
        for faculty_schedule in faculty_data.values():
            for day_schedule in faculty_schedule.values():
                stats["total_hours"] += len(day_schedule)
                stats["busy_hours"] += sum(1 for busy in day_schedule.values() if busy)
        
        stats["free_hours"] = stats["total_hours"] - stats["busy_hours"]
        
        return stats
    except Exception as e:
        print(f"Error calculating faculty statistics: {e}")
        return {}

def generate_utilization_report(rooms_data, faculty_data):
    """
    Generate comprehensive utilization report
    Returns dict with complete analysis
    """
    try:
        report = {
            "timestamp": datetime.now().isoformat(),
            "room_statistics": calculate_room_statistics(rooms_data),
            "faculty_statistics": calculate_faculty_statistics(faculty_data),
            "room_utilization": calculate_room_utilization(rooms_data),
            "faculty_workload": calculate_faculty_workload(faculty_data),
            "peak_hours": get_peak_hours_analysis(rooms_data),
            "daily_trends": get_daily_utilization_trends(rooms_data)
        }
        
        return report
    except Exception as e:
        print(f"Error generating utilization report: {e}")
        return {}

def export_analytics_data(rooms_data, faculty_data, format="json"):
    """
    Export analytics data in specified format
    Returns formatted data string
    """
    try:
        report = generate_utilization_report(rooms_data, faculty_data)
        
        if format.lower() == "json":
            return json.dumps(report, indent=2, ensure_ascii=False)
        elif format.lower() == "csv":
            # Basic CSV export implementation
            csv_lines = ["Metric,Value"]
            
            # Room statistics
            room_stats = report.get("room_statistics", {})
            for key, value in room_stats.items():
                csv_lines.append(f"room_{key},{value}")
            
            # Faculty statistics
            faculty_stats = report.get("faculty_statistics", {})
            for key, value in faculty_stats.items():
                csv_lines.append(f"faculty_{key},{value}")
            
            return "\n".join(csv_lines)
        else:
            return str(report)
    except Exception as e:
        print(f"Error exporting analytics data: {e}")
        return ""

# Helper function for data validation
def validate_data_structure(data, data_type="rooms"):
    """
    Validate data structure for analytics
    Returns True if valid, False otherwise
    """
    try:
        if not isinstance(data, dict):
            return False
        
        for entity, schedule in data.items():
            if not isinstance(schedule, dict):
                return False
            
            for day, slots in schedule.items():
                if not isinstance(slots, dict):
                    return False
                
                for slot, status in slots.items():
                    if not isinstance(status, bool):
                        return False
        
        return True
    except Exception:
        return False
