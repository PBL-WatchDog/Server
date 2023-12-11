from datetime import datetime, timedelta, timezone

def calculate_days(start_date_obj : datetime, end_date_obj : datetime, offset : int): 
    start_date_obj = get_local_datetime(start_date_obj, offset)
    end_date_obj = get_local_datetime(end_date_obj, offset)
    
    days = (end_date_obj.date() - start_date_obj.date()).days + 1

    return days

def get_local_datetime(date_obj : datetime, offset : int):
    if not date_obj:
        return None
    
    offset_timezone = timezone(timedelta(minutes=-offset))

    local_date_obj = date_obj.astimezone(offset_timezone)

    return local_date_obj

def get_utc_isoformat(date_obj, offset=0):
    if not date_obj:
        return None

    offset_timedelta = timedelta(minutes=offset)
    utc_date_obj = date_obj - offset_timedelta
    return utc_date_obj.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')

def get_datetime_by_utc_isoformat(formmat : str):
    try:
        return datetime.strptime(formmat, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc) 
    except:
        return None