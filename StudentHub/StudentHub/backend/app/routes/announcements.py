"""
routes/announcements.py
Admin can broadcast to everyone or a department/semester; Faculty can
only notify their own assigned classes (their subjects' department +
semester). Supports future scheduling (a background worker/cron would
publish scheduled_for ones — noted in README as a Phase 2.5 task).
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from app.database import announcements_collection, students_collection, faculty_collection, subjects_collection, users_collection
from app.auth import require_role
from app.models.announcement import new_announcement_document
from app.schemas.operations import CreateAnnouncementRequest
from app.services.notifications import notify_many

router = APIRouter(prefix="/announcements", tags=["Announcements"])


async def _recipients_for(target_type: str, department: str | None, semester: int | None) -> list[str]:
    query: dict = {}
    if target_type in ("department", "semester") and department:
        query["department"] = department
    if target_type == "semester" and semester:
        query["semester"] = semester
    students = await students_collection.find(query).to_list(length=10000)
    return [s["user_id"] for s in students]


@router.post("", status_code=201)
async def create_announcement(payload: CreateAnnouncementRequest, user=Depends(require_role("admin", "faculty"))):
    if user["role"] == "faculty":
        # Faculty can only broadcast to their own assigned classes.
        faculty = await faculty_collection.find_one({"user_id": user["_id"]})
        if not faculty or not faculty.get("subject_ids"):
            raise HTTPException(403, "You have no assigned classes to notify.")
        subjects = await subjects_collection.find({"_id": {"$in": faculty["subject_ids"]}}).to_list(length=100)
        allowed_depts = {s["department"] for s in subjects}
        if payload.target_type != "all" or (payload.department and payload.department not in allowed_depts):
            pass  # allow — but recipients below are still restricted to faculty's own subjects
        # Force targeting to faculty's own subjects, regardless of what was submitted.
        recipient_ids = set()
        for s in subjects:
            students = await students_collection.find({"department": s["department"], "semester": s["semester"]}).to_list(length=5000)
            recipient_ids.update(st["user_id"] for st in students)
        recipient_ids = list(recipient_ids)
    else:
        recipient_ids = await _recipients_for(payload.target_type, payload.department, payload.semester)

    doc = new_announcement_document(
        title=payload.title, message=payload.message, created_by=user["_id"],
        target_type=payload.target_type, department=payload.department,
        semester=payload.semester, scheduled_for=payload.scheduled_for,
    )
    await announcements_collection.insert_one(doc)

    # If not scheduled for the future, notify immediately.
    is_future = False
    if payload.scheduled_for:
        try:
            is_future = datetime.fromisoformat(payload.scheduled_for) > datetime.now(timezone.utc)
        except ValueError:
            is_future = False

    if not is_future:
        await notify_many(recipient_ids, payload.title, payload.message, "new_announcement", link="/announcements")

    return {"message": "Announcement published." if not is_future else "Announcement scheduled.", "id": doc["_id"]}


@router.get("")
async def list_announcements(user=Depends(require_role("admin", "faculty", "student"))):
    now = datetime.now(timezone.utc).isoformat()
    # Only show announcements that are already due (scheduled_for is null or in the past).
    query = {"$or": [{"scheduled_for": None}, {"scheduled_for": {"$lte": now}}]}
    announcements = await announcements_collection.find(query).sort("created_at", -1).to_list(length=500)
    return [{**a, "id": a["_id"]} for a in announcements]
