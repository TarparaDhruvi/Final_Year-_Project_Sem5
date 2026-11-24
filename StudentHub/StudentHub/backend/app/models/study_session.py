"""models/study_session.py — `study_sessions` collection: one document per Focus Mode session."""
import uuid
from datetime import datetime, timezone


def new_session_document(user_id: str, subject_id: str | None, goal_minutes: int) -> dict:
    return {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "subject_id": subject_id,
        "goal_minutes": goal_minutes,
        "started_at": datetime.now(timezone.utc),
        "ended_at": None,
        "actual_minutes": None,
        "completed": False,
    }
