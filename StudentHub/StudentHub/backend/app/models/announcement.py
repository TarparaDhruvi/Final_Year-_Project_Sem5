"""models/announcement.py — the `announcements` collection."""
import uuid
from datetime import datetime, timezone


def new_announcement_document(
    title: str, message: str, created_by: str, target_type: str,
    department: str | None = None, semester: int | None = None, scheduled_for: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": str(uuid.uuid4()),
        "title": title,
        "message": message,
        "created_by": created_by,
        "target_type": target_type,   # "all" | "department" | "semester" | "class"
        "department": department,
        "semester": semester,
        "scheduled_for": scheduled_for,   # ISO datetime string, null = publish immediately
        "created_at": now,
    }
