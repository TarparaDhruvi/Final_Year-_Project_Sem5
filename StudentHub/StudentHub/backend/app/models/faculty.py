"""models/faculty.py — the `faculty` collection: academic profile, keyed to a `users` row by user_id."""
import uuid
from datetime import datetime, timezone


def new_faculty_document(user_id: str, faculty_id: str, department: str, designation: str | None = None) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "faculty_id": faculty_id,
        "department": department,
        "designation": designation,
        "subject_ids": [],
        "created_at": now,
        "updated_at": now,
    }
