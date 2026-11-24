"""
services/deadlines.py
Smart Deadline Reminder support: records each login and, for students,
detects what they missed while away (assignment deadlines that passed,
announcements that were posted) — used to power the one-time "Welcome
back" recovery popup on the frontend right after login.
"""

from datetime import datetime, timezone
from app.database import (
    login_history_collection, students_collection, subjects_collection,
    assignments_collection, submissions_collection, announcements_collection,
)
from app.models.login_history import new_login_history_document


async def record_login(user_id: str, role: str) -> dict:
    """Inserts this login and returns the PREVIOUS login record (or None if first-ever login)."""
    previous = await login_history_collection.find_one(
        {"user_id": user_id}, sort=[("login_at", -1)]
    )
    await login_history_collection.insert_one(new_login_history_document(user_id, role))
    return previous


async def compute_missed_activity(user_id: str, previous_login: dict | None) -> dict | None:
    """
    Returns None if there's nothing worth showing (first-ever login, or
    away for less than 2 days). Otherwise returns a summary of assignment
    deadlines that passed and announcements posted during the gap.
    """
    if not previous_login:
        return None

    last_login_at = previous_login["login_at"]
    if last_login_at.tzinfo is None:
        last_login_at = last_login_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    days_away = (now - last_login_at).days
    if days_away < 2:
        return None

    student = await students_collection.find_one({"user_id": user_id})
    if not student:
        return None

    subjects = await subjects_collection.find(
        {"department": student["department"], "semester": student["semester"]}
    ).to_list(length=100)
    subject_ids = [s["_id"] for s in subjects]
    subjects_by_id = {s["_id"]: s for s in subjects}

    gap_start_date = last_login_at.date().isoformat()
    today_date = now.date().isoformat()

    assignments = await assignments_collection.find(
        {"subject_id": {"$in": subject_ids}, "due_date": {"$gte": gap_start_date, "$lt": today_date}}
    ).to_list(length=200)

    missed_assignments = []
    for a in assignments:
        submission = await submissions_collection.find_one(
            {"assignment_id": a["_id"], "student_id": student["_id"], "status": {"$in": ["submitted", "graded"]}}
        )
        if not submission:
            missed_assignments.append({
                "title": a["title"],
                "subject_name": subjects_by_id.get(a["subject_id"], {}).get("name", "Subject"),
                "due_date": a["due_date"],
            })

    announcements = await announcements_collection.find(
        {"created_at": {"$gte": last_login_at, "$lte": now}}
    ).sort("created_at", -1).to_list(length=50)
    new_announcements = [{"title": a["title"], "message": a["message"]} for a in announcements]

    if not missed_assignments and not new_announcements:
        return None

    return {
        "days_away": days_away,
        "missed_assignments": missed_assignments,
        "new_announcements": new_announcements,
    }
