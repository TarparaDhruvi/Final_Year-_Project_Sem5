"""models/subject.py — the `subjects` collection.

Who teaches a subject is NOT stored here. Teachers are linked through the `faculty_subjects` collection
(many-to-many; see services/faculty_subject_links.py). Older documents may still carry a legacy
`faculty_id` field: it is ignored after the one-time migration and is never deleted.
"""
import uuid
from datetime import datetime, timezone


def new_subject_document(name: str, code: str, department: str, semester: int, credits: int = 3) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": str(uuid.uuid4()),
        "name": name,
        "code": code,
        "department": department,
        "semester": semester,
        "credits": credits,
        "created_at": now,
        "updated_at": now,
    }
