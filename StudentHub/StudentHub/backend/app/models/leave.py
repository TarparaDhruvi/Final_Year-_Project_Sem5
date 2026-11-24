"""models/leave.py — the `leave_requests` collection."""
import uuid
from datetime import datetime, timezone


def new_leave_document(user_id: str, role: str, reason: str, from_date: str, to_date: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "role": role,               # "student" | "faculty"
        "reason": reason,
        "from_date": from_date,
        "to_date": to_date,
        "status": "pending",        # pending | approved | rejected
        "reviewed_by": None,
        "reviewed_at": None,
        "applied_at": now,
    }
