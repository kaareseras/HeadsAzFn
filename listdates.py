import datetime


import datetime
from typing import Union

def listdates(_date: datetime.datetime | datetime.date) -> list[datetime.date]:
    """
    Returns a list of dates from the day after _date up to (and including) tomorrow.
    Accepts either a datetime.datetime or datetime.date object.
    """
    if isinstance(_date, datetime.datetime):
        last_date = _date.date()
    elif isinstance(_date, datetime.date):
        last_date = _date
    elif isinstance(_date, str):
        try:
            last_date = datetime.datetime.fromisoformat(_date).date()
        except ValueError:
            raise ValueError("String date must be in ISO format: 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS.ssssss'")
    else:
        raise TypeError("Expected datetime.date, datetime.datetime, or ISO format string")

    current_date = datetime.datetime.now().date()
    next_date = last_date + datetime.timedelta(days=1)
    end_date = current_date + datetime.timedelta(days=1)

    dates = []
    while next_date <= end_date:
        dates.append(next_date)
        next_date += datetime.timedelta(days=1)

    return dates