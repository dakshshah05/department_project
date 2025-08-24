# Saturday scheduling utilities - all Saturdays except 3rd Saturday
from datetime import datetime, date
import calendar

def is_working_saturday(check_date):
    """
    Check if a given Saturday is a working day
    Returns False for 3rd Saturday of each month (holiday)
    """
    if check_date.weekday() != 5:  # Not a Saturday
        return True
    
    # Get the first day of the month
    first_day = date(check_date.year, check_date.month, 1)
    
    # Find the first Saturday of the month
    days_until_saturday = (5 - first_day.weekday()) % 7
    first_saturday = first_day.day + days_until_saturday
    
    # Calculate which Saturday this is
    saturday_number = ((check_date.day - first_saturday) // 7) + 1
    
    # 3rd Saturday is holiday
    return saturday_number != 3

def get_saturday_schedule(year, month):
    """
    Get Saturday schedule for a given month
    Returns list of working and holiday Saturdays
    """
    saturdays = []
    
    # Get all Saturdays in the month
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        if week[5] != 0:  # Saturday is index 5, 0 means not in this month
            saturday_date = date(year, month, week[5])
            is_working = is_working_saturday(saturday_date)
            
            saturdays.append({
                'date': saturday_date,
                'is_working': is_working,
                'week_number': len([s for s in saturdays if s.get('is_working', True)]) + 1
            })
    
    return saturdays

def get_next_working_saturday(from_date=None):
    """Get the next working Saturday from given date"""
    if from_date is None:
        from_date = date.today()
    
    current_date = from_date
    
    # Find next Saturday
    while current_date.weekday() != 5:
        current_date = current_date.replace(day=current_date.day + 1)
    
    # Check if it's working
    while not is_working_saturday(current_date):
        # Move to next Saturday
        current_date = current_date.replace(day=current_date.day + 7)
    
    return current_date

def format_saturday_info(check_date):
    """Format Saturday information for display"""
    if check_date.weekday() != 5:
        return "Not a Saturday"
    
    if is_working_saturday(check_date):
        return "Working Saturday ✅"
    else:
        return "Holiday - 3rd Saturday 🎉"
