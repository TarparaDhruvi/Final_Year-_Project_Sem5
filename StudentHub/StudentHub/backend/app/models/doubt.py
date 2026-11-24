"""models/doubt.py — `doubts` collection: anonymous student questions, faculty replies, upvotes."""
import uuid
from datetime import datetime, timezone


def new_doubt_document(subject_id: str, asked_by_user_id: str, question: str) -> dict:
    return {
        "_id": str(uuid.uuid4()),
        "subject_id": subject_id,
        "asked_by_user_id": asked_by_user_id,   # kept for moderation only — NEVER returned to other students
        "question": question,
        "reply": None,
        "replied_by": None,
        "replied_at": None,
        "upvoted_by": [],   # list of user_ids, so a user can only upvote once
        "created_at": datetime.now(timezone.utc),
    }
