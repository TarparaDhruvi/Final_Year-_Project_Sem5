"""
models/submission.py — the `submissions` collection.
`timeline` powers the "Assignment DNA" feature: an ordered log of events
(draft created, updated, final submitted) for this submission.
"""
import uuid
from datetime import datetime, timezone


def new_submission_document(assignment_id: str, student_id: str, file_url: str | None = None) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": str(uuid.uuid4()),
        "assignment_id": assignment_id,
        "student_id": student_id,
        "file_url": file_url,
        "status": "draft" if not file_url else "submitted",   # draft | submitted | graded
        "grade": None,
        "feedback": None,
        "submitted_at": now if file_url else None,
        "timeline": [
            {"event": "Draft Created" if not file_url else "Final Submitted", "at": now.isoformat()}
        ],
        "created_at": now,
        "updated_at": now,
    }


def timeline_event(event: str) -> dict:
    return {"event": event, "at": datetime.now(timezone.utc).isoformat()}
