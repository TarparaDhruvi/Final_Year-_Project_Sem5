"""models/assignment.py — the `assignments` collection."""
import uuid
from datetime import datetime, timezone


def new_assignment_document(
    title: str, description: str, subject_id: str, faculty_id: str,
    due_date: str, instructions_file_url: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": str(uuid.uuid4()),
        "title": title,
        "description": description,
        "subject_id": subject_id,
        "faculty_id": faculty_id,
        "due_date": due_date,      # ISO date string
        "instructions_file_url": instructions_file_url,
        "created_at": now,
        "updated_at": now,
    }
