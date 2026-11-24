"""models/note.py — the `uploaded_notes` collection: faculty-uploaded study material."""
import uuid
from datetime import datetime, timezone


def new_note_document(title: str, subject_id: str, unit: str, semester: int, file_url: str, file_type: str, uploaded_by: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": str(uuid.uuid4()),
        "title": title,
        "subject_id": subject_id,
        "unit": unit,
        "semester": semester,
        "file_url": file_url,
        "file_type": file_type,   # pdf | ppt | docx | image
        "uploaded_by": uploaded_by,
        "views": 0,
        "created_at": now,
    }
