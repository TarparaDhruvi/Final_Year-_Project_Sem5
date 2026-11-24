"""
utils/dates.py
Shared "no past dates" validation used by assignments, exams, leave
requests, and announcement scheduling — each of those needs the same
rule (a date must be today or later) with a feature-specific message.
"""

from datetime import date, datetime


def parse_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return datetime.fromisoformat(str(value)).date()


def reject_past_date(value, label: str = "Date") -> str | None:
    """Returns an error message, or None if the date is today or in the future."""
    try:
        d = parse_date(value)
    except (ValueError, TypeError):
        return f"{label} is not a valid date."
    if d < date.today():
        return f"{label} cannot be in the past."
    return None
