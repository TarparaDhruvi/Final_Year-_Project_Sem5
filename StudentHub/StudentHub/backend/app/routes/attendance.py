"""
routes/attendance.py
Faculty mark/edit attendance for their subjects; students see their own
subject-wise attendance plus a simple "skip N classes -> attendance
becomes X%" prediction.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.database import attendance_collection, students_collection, subjects_collection, faculty_collection
from app.auth import require_role, get_current_user
from app.models.attendance import new_attendance_document
from app.schemas.operations import MarkAttendanceRequest, UpdateAttendanceRequest
from app.routes.skill_wallet import award_xp
from app.services.access import assert_can_manage_subject, assert_students_enrolled
from app.utils.timeutil import local_today
from datetime import date as _date

router = APIRouter(prefix="/attendance", tags=["Attendance"])


def _validate_attendance_date(value: str) -> str:
    try:
        d = _date.fromisoformat(str(value)[:10])
    except ValueError:
        raise HTTPException(400, "Attendance date is not a valid date.")
    if d > local_today():
        raise HTTPException(400, "Attendance cannot be marked for a future date.")
    return d.isoformat()


@router.post("/mark")
async def mark_attendance(payload: MarkAttendanceRequest, user=Depends(require_role("faculty", "admin"))):
    subject = await assert_can_manage_subject(user, payload.subject_id)
    day = _validate_attendance_date(payload.date)
    if not payload.entries:
        raise HTTPException(400, "No students were provided.")
    students_by_id = await assert_students_enrolled([e.student_id for e in payload.entries], subject)

    for entry in payload.entries:
        existing = await attendance_collection.find_one(
            {"subject_id": payload.subject_id, "student_id": entry.student_id, "date": day}
        )
        if existing:
            await attendance_collection.update_one(
                {"_id": existing["_id"]}, {"$set": {"status": entry.status, "updated_at": datetime.now(timezone.utc)}}
            )
        else:
            doc = new_attendance_document(payload.subject_id, entry.student_id, day, entry.status, user["_id"])
            await attendance_collection.insert_one(doc)
            if entry.status == "present":
                await award_xp(students_by_id[entry.student_id]["user_id"], "attendance")

    return {"message": f"Attendance marked for {len(payload.entries)} student(s)."}


@router.put("/{attendance_id}")
async def edit_attendance(attendance_id: str, payload: UpdateAttendanceRequest, user=Depends(require_role("faculty", "admin"))):
    record = await attendance_collection.find_one({"_id": attendance_id})
    if not record:
        raise HTTPException(404, "Attendance record not found.")
    await assert_can_manage_subject(user, record["subject_id"])
    await attendance_collection.update_one({"_id": attendance_id}, {"$set": {"status": payload.status, "updated_at": datetime.now(timezone.utc)}})
    return {"message": "Attendance updated."}


@router.get("/subject/{subject_id}")
async def view_subject_attendance(subject_id: str, date: Optional[str] = None, user=Depends(require_role("faculty", "admin"))):
    await assert_can_manage_subject(user, subject_id)
    query: dict = {"subject_id": subject_id}
    if date:
        query["date"] = date
    records = await attendance_collection.find(query).to_list(length=5000)
    return [{**r, "id": r["_id"]} for r in records]


@router.get("/me")
async def my_attendance(user=Depends(require_role("student"))):
    """Subject-wise attendance % for the logged-in student, with a simple prediction."""
    student = await students_collection.find_one({"user_id": user["_id"]})
    if not student:
        raise HTTPException(404, "Student profile not found.")

    records = await attendance_collection.find({"student_id": student["_id"]}).to_list(length=5000)
    by_subject: dict = {}
    for r in records:
        s = by_subject.setdefault(r["subject_id"], {"present": 0, "total": 0})
        s["total"] += 1
        if r["status"] == "present":
            s["present"] += 1

    subject_ids = list(by_subject.keys())
    subjects = await subjects_collection.find({"_id": {"$in": subject_ids}}).to_list(length=1000)
    subjects_by_id = {s["_id"]: s for s in subjects}

    result = []
    for subject_id, counts in by_subject.items():
        total, present = counts["total"], counts["present"]
        percentage = round((present / total) * 100, 1) if total else 0.0

        # Prediction: how does % change after N more consecutive absences?
        predicted_after_2_skips = round((present / (total + 2)) * 100, 1) if total else 0.0

        result.append({
            "subject_id": subject_id,
            "subject_name": subjects_by_id.get(subject_id, {}).get("name", "Unknown"),
            "present": present,
            "total": total,
            "percentage": percentage,
            "prediction_after_2_more_absences": predicted_after_2_skips,
            "at_risk": percentage < 75,
        })
    return result
