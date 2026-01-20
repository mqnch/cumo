import re
from datetime import datetime, timedelta
from typing import Optional, Tuple


TIME_PATTERNS = [
    (r'\b(\d{1,2})\s*(?:am|pm)\b', '12h'), 
    (r'\bat\s+(\d{1,2})\s*(?:am|pm)?\b', 'at_12h'), 
    (r'@(\d{1,2})(?:\s*(?:am|pm))?\b', 'at_12h'), 
    (r'@\s+(\d{1,2})\s*(?:am|pm)?\b', 'at_12h'), 
    (r'\b(\d{1,2}):(\d{2})\s*(?:am|pm)?\b', '24h'), 
    (r'@(\d{1,2}):(\d{2})(?:\s*(?:am|pm))?\b', '24h'), 
    (r'@\s+(\d{1,2}):(\d{2})\s*(?:am|pm)?\b', '24h'), 
    (r'\bnoon\b', 'noon'), 
    (r'\bmidnight\b', 'midnight'), 
    (r'\bat\s+night\b', 'at_night'), 
]


RELATIVE_TIME_PATTERNS = [
    (r'\bin\s+(\d+)\s+hours?\b', 'hours'),
    (r'\bin\s+(\d+)\s+minutes?\b', 'minutes'),
    (r'\bin\s+(\d+)\s+days?\b', 'days'),
]

TIME_RANGE_PATTERNS = [
    (r'now\s*-\s*(\d{1,2})\s*(am|pm)', 'range_now_12h'),
    (r'now\s+to\s+(\d{1,2})\s*(am|pm)', 'range_now_12h_to'),
    (r'(\d{1,2})\s*-\s*(\d{1,2})\s*(am|pm)', 'range_12h'),
    (r'(\d{1,2})\s+to\s+(\d{1,2})\s*(am|pm)', 'range_12h_to'),
    (r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*(am|pm)?', 'range_24h'),
]


def extract_explicit_time(text: str, base_date: Optional[datetime] = None) -> Optional[Tuple[int, int]]:
    if base_date is None:
        base_date = datetime.now()
    
    text_lower = text.lower()
    
    if re.search(r'\bnoon\b', text_lower):
        return (12, 0)
    if re.search(r'\bmidnight\b', text_lower):
        return (0, 0)
    if re.search(r'\bat\s+night\b', text_lower):
        return (20, 0)
    
    for pattern, pattern_type in TIME_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            if pattern_type == '12h':
                hour = int(match.group(1))

                if 'pm' in match.group(0).lower() and hour != 12:
                    hour += 12
                elif 'am' in match.group(0).lower() and hour == 12:
                    hour = 0
                return (hour, 0)
            
            elif pattern_type == 'at_12h':
                hour = int(match.group(1))
                full_match = match.group(0).lower()

                if 'pm' in full_match and hour != 12:
                    hour += 12
                elif 'am' in full_match and hour == 12:
                    hour = 0
                return (hour, 0)
            
            elif pattern_type == 'at_night':
                return (20, 0)
            
            elif pattern_type == '24h':
                hour = int(match.group(1))
                minute = int(match.group(2))

                if 'pm' in match.group(0).lower() and hour != 12:
                    hour += 12
                elif 'am' in match.group(0).lower() and hour == 12:
                    hour = 0
                return (hour, minute)
    
    return None


def extract_relative_time(text: str, base_date: Optional[datetime] = None) -> Optional[datetime]:
    if base_date is None:
        base_date = datetime.now()
    
    text_lower = text.lower()
    
    for pattern, unit in RELATIVE_TIME_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            value = int(match.group(1))
            if unit == 'hours':
                return base_date + timedelta(hours=value)
            elif unit == 'minutes':
                return base_date + timedelta(minutes=value)
            elif unit == 'days':
                return base_date + timedelta(days=value)
    
    return None


def normalize_text(text: str) -> str:
    normalized = text.lower().strip()
    normalized = normalized.replace('@', 'at')
    
    abbreviations = {
        r'\btmr\b': 'tomorrow',
        r'\byest\b': 'yesterday',
        r'\btdy\b': 'today',
        r'\btn\b': 'tonight'
    }
    
    for abbrev, full in abbreviations.items():
        normalized = re.sub(abbrev, full, normalized)
    
    return normalized


def extract_time_range(text: str, base_date: Optional[datetime] = None) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
    if base_date is None:
        base_date = datetime.now()
    
    text_lower = text.lower()
    
    for pattern, pattern_type in TIME_RANGE_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            if pattern_type == 'range_now_12h':
                end_hour = int(match.group(1))
                period = match.group(2).lower()
                
                if period == 'pm':
                    if end_hour != 12:
                        end_hour += 12
                elif period == 'am':
                    if end_hour == 12:
                        end_hour = 0
                
                start_time = (base_date.hour, base_date.minute)
                return (start_time, (end_hour, 0))
            
            elif pattern_type == 'range_now_12h_to':
                end_hour = int(match.group(1))
                period = match.group(2).lower()
                
                if period == 'pm':
                    if end_hour != 12:
                        end_hour += 12
                elif period == 'am':
                    if end_hour == 12:
                        end_hour = 0
                
                start_time = (base_date.hour, base_date.minute)
                return (start_time, (end_hour, 0))
            
            elif pattern_type == 'range_12h':
                start_hour = int(match.group(1))
                end_hour = int(match.group(2))
                period = match.group(3).lower()
                
                if period == 'pm':
                    if start_hour != 12:
                        start_hour += 12
                    if end_hour != 12:
                        end_hour += 12
                elif period == 'am':
                    if start_hour == 12:
                        start_hour = 0
                    if end_hour == 12:
                        end_hour = 0
                
                return ((start_hour, 0), (end_hour, 0))
            
            elif pattern_type == 'range_12h_to':
                start_hour = int(match.group(1))
                end_hour = int(match.group(2))
                period = match.group(3).lower()
                
                if period == 'pm':
                    if start_hour != 12:
                        start_hour += 12
                    if end_hour != 12:
                        end_hour += 12
                elif period == 'am':
                    if start_hour == 12:
                        start_hour = 0
                    if end_hour == 12:
                        end_hour = 0
                
                return ((start_hour, 0), (end_hour, 0))
            
            elif pattern_type == 'range_24h':
                start_hour = int(match.group(1))
                start_minute = int(match.group(2))
                end_hour = int(match.group(3))
                end_minute = int(match.group(4))
                period = match.group(5).lower() if match.group(5) else None
                
                if period == 'pm':
                    if start_hour != 12:
                        start_hour += 12
                    if end_hour != 12:
                        end_hour += 12
                elif period == 'am':
                    if start_hour == 12:
                        start_hour = 0
                    if end_hour == 12:
                        end_hour = 0
                
                return ((start_hour, start_minute), (end_hour, end_minute))

    return None


def merge_datetime_time(date_obj: datetime, time_tuple: Optional[Tuple[int, int]]) -> datetime:
    if time_tuple is None:
        return date_obj
    
    hour, minute = time_tuple
    return date_obj.replace(hour=hour, minute=minute, second=0, microsecond=0)
