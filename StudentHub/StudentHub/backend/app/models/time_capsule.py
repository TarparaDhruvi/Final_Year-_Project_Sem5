"""models/time_capsule.py — `time_capsule` collection: a message a student schedules for their future self."""
import uuid
from datetime import datetime, timezone


def new_capsule_document(user_id: str, title: str, message: str, unlock_date: str) -> dict:
    return {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": title,
        "message": message,
        "unlock_date": unlock_date,   # ISO date string
        "opened": False,
        "opened_at": None,
        "created_at": datetime.now(timezone.utc),
    }
