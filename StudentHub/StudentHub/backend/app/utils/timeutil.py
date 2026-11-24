"""
utils/timeutil.py
One place for "what day/time is it for the college?". The server may run in UTC, but
deadlines like "due today 11:59 PM" must follow the campus time zone (APP_TIMEZONE,
default Asia/Kolkata), otherwise Indian students see wrong "due today" flags.
"""
import os
from datetime import datetime, date, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo(os.getenv("APP_TIMEZONE", "Asia/Kolkata"))
except Exception:                                   # tzdata missing (e.g. bare Windows)
    _TZ = timezone(timedelta(hours=5, minutes=30))  # IST fallback


def local_now() -> datetime:
    return datetime.now(_TZ)


def local_today() -> date:
    return local_now().date()


def today_str() -> str:
    return local_today().isoformat()


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(str(value)[:10])
