"""models/attendance.py — the `attendance` collection. One document per student per subject per date."""
import uuid
from datetime import datetime, timezone


def new_attendance_document(subject_id: str, student_id: str, date_str: str, status: str, marked_by: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": str(uuid.uuid4()),
        "subject_id": subject_id,
        "student_id": student_id,
        "date": date_str,          # ISO date string, e.g. "2026-09-26"
        "status": status,          # "present" | "absent"
        "marked_by": marked_by,    # faculty user_id
        "created_at": now,
        "updated_at": now,
    }
