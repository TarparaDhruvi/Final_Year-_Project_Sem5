"""models/skill_wallet.py — `skill_wallet` collection: one XP-award document per activity."""
import uuid
from datetime import datetime, timezone

XP_TABLE = {
    "attendance": 5,
    "early_submission": 20,
    "on_time_submission": 10,
    "event": 50,
    "helping_others": 10,
    "perfect_attendance_week": 15,
}

BADGES = [
    {"id": "early_bird", "name": "Early Bird", "description": "Submit 5 assignments before their due date.", "check": lambda xp, counts: counts.get("early_submission", 0) >= 5},
    {"id": "attendance_king", "name": "Attendance King", "description": "Earn attendance XP 20 times.", "check": lambda xp, counts: counts.get("attendance", 0) >= 20},
    {"id": "coding_master", "name": "Coding Master", "description": "Reach 500 total XP.", "check": lambda xp, counts: xp >= 500},
    {"id": "helper", "name": "Helping Hand", "description": "Get credited for helping others 5 times.", "check": lambda xp, counts: counts.get("helping_others", 0) >= 5},
    {"id": "century", "name": "Century Club", "description": "Reach 100 total XP.", "check": lambda xp, counts: xp >= 100},
]


def new_xp_document(user_id: str, activity: str, xp: int, note: str | None = None) -> dict:
    return {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "activity": activity,
        "xp": xp,
        "note": note,
        "created_at": datetime.now(timezone.utc),
    }
