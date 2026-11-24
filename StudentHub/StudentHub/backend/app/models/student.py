"""models/student.py — the `students` collection: academic profile, keyed to a `users` row by user_id."""
import uuid
from datetime import datetime, timezone


def new_student_document(user_id: str, student_id: str, department: str, semester: int, batch: str | None = None) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "student_id": student_id,
        "department": department,
        "semester": semester,
        "batch": batch,
        "created_at": now,
        "updated_at": now,
    }
