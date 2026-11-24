"""models/timetable.py — the `timetable` collection. One document per scheduled slot."""
import uuid
from datetime import datetime, timezone


def new_timetable_document(
    day_of_week: str, start_time: str, end_time: str, subject_id: str,
    faculty_id: str, classroom: str, department: str, semester: int,
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": str(uuid.uuid4()),
        "day_of_week": day_of_week,   # "Monday".."Saturday"
        "start_time": start_time,     # "09:00"
        "end_time": end_time,         # "10:00"
        "subject_id": subject_id,
        "faculty_id": faculty_id,
        "classroom": classroom,
        "department": department,
        "semester": semester,
        "created_at": now,
        "updated_at": now,
    }
