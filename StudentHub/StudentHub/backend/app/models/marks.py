"""models/marks.py — the `marks` collection. One document per student per subject."""
import uuid
from datetime import datetime, timezone


def new_marks_document(student_id: str, subject_id: str, internal: float | None = None, practical: float | None = None) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": str(uuid.uuid4()),
        "student_id": student_id,
        "subject_id": subject_id,
        "internal": internal,
        "practical": practical,
        "published": False,
        "created_at": now,
        "updated_at": now,
    }
