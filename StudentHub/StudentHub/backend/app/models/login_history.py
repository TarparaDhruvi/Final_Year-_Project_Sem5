"""models/login_history.py — the `login_history` collection. Powers the Smart Deadline Reminder's missed-activity recovery."""
import uuid
from datetime import datetime, timezone


def new_login_history_document(user_id: str, role: str) -> dict:
    return {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "role": role,
        "login_at": datetime.now(timezone.utc),
    }
