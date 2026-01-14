from datetime import datetime, timedelta

def calculate_next_heat(last_heat_date_str):
    """
    Calculates the expected date of the next estrus cycle (avg 21 days).
    Format: YYYY-MM-DD
    """
    try:
        last_date = datetime.strptime(last_heat_date_str, "%Y-%m-%d")
        # Cows cycle every 18-24 days, average is 21
        next_cycle_start = last_date + timedelta(days=18)
        next_cycle_end = last_date + timedelta(days=24)
        
        return {
            "window_start": next_cycle_start.strftime("%Y-%m-%d"),
            "window_end": next_cycle_end.strftime("%Y-%m-%d")
        }
    except ValueError:
        return None

def analyze_bcs(score):
    """
    Returns a health warning based on Body Condition Score (1-5).
    Ideal for breeding is usually 3.0 - 3.5.
    """
    if score < 2.5:
        return "⚠️ Underweight: Conception rates significantly lower."
    elif score > 4.0:
        return "⚠️ Overweight: Risk of metabolic issues and calving difficulty."
    else:
        return "✅ Optimal Body Condition."

def am_pm_rule(heat_detection_time):
    """
    Applies the AM/PM rule for AI timing.
    - Heat seen in AM -> Inseminate in PM.
    - Heat seen in PM -> Inseminate next day AM.
    """
    hour = heat_detection_time.hour
    if 0 <= hour < 12:
        return "Recommendation: Inseminate this evening (PM)."
    else:
        return "Recommendation: Inseminate tomorrow morning (AM)."