def time_str_to_seconds(time_str: str) -> float:
    """
    Convert time string 'HH.MM' or 'HH:MM:SS' into total seconds.
    If input is '00.30', it means 0 hours and 30 minutes.
    If input is string '120', it behaves as seconds.
    """
    if not time_str:
        return 0.0
    
    time_str = str(time_str).strip()
    
    # Handle pure seconds input
    if time_str.isdigit():
        return float(time_str)

    # Handle HH.MM format (as requested by user: 00.30 = 30 mins, 01.20 = 1h 20m)
    if '.' in time_str and ':' not in time_str:
        parts = time_str.split('.')
        if len(parts) == 2:
            hours = int(parts[0])
            minutes = int(parts[1])
            return hours * 3600 + minutes * 60
        elif len(parts) == 3: # Handle rare HH.MM.SS if user tries it
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds

    # Handle standard HH:MM:SS or MM:SS
    parts = time_str.split(':')
    total_seconds = 0
    if len(parts) == 3:
        total_seconds += int(parts[0]) * 3600
        total_seconds += int(parts[1]) * 60
        total_seconds += float(parts[2])
    elif len(parts) == 2:
        total_seconds += int(parts[0]) * 60
        total_seconds += float(parts[1])
    else:
        try:
            total_seconds = float(time_str)
        except ValueError:
            return 0.0
            
    return total_seconds

def seconds_to_hms(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"
