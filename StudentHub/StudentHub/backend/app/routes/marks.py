"""
routes/marks.py
Faculty enter internal/practical marks and publish results; students see
only published marks for their own subjects.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.database import marks_collection, subjects_collection, faculty_collection, students_collection
from app.auth import require_role
from app.models.marks import new_marks_document
from app.schemas.marks import SetMarksRequest
from app.services.notifications import notify_user
from app.services.access import assert_can_manage_subject, assert_students_enrolled
from datetime import datetime, timezone

router = APIRouter(prefix="/marks", tags=["Marks"])


@router.put("")
async def set_marks(payload: SetMarksRequest, user=Depends(require_role("faculty", "admin"))):
    subject = await assert_can_manage_subject(user, payload.subject_id)
    await assert_students_enrolled([payload.student_id], subject)
    fields = {k: v for k, v in {"internal": payload.internal, "practical": payload.practical}.items() if v is not None}
    if not fields:
        raise HTTPException(400, "Enter internal and/or practical marks.")
    fields["updated_at"] = datetime.now(timezone.utc)

    existing = await marks_collection.find_one({"student_id": payload.student_id, "subject_id": payload.subject_id})
    if existing:
        await marks_collection.update_one({"_id": existing["_id"]}, {"$set": fields})
    else:
        doc = new_marks_document(payload.student_id, payload.subject_id, payload.internal, payload.practical)
        await marks_collection.insert_one(doc)
    return {"message": "Marks saved."}


@router.put("/{marks_id}/publish")
async def publish_marks(marks_id: str, user=Depends(require_role("faculty", "admin"))):
    record = await marks_collection.find_one({"_id": marks_id})
    if not record:
        raise HTTPException(404, "Marks record not found.")
    await assert_can_manage_subject(user, record["subject_id"])
    await marks_collection.update_one({"_id": marks_id}, {"$set": {"published": True, "updated_at": datetime.now(timezone.utc)}})

    student = await students_collection.find_one({"_id": record["student_id"]})
    if student:
        await notify_user(student["user_id"], "Results Published", "Your marks have been published.", "assignment_reminder")
    return {"message": "Marks published."}


@router.get("/subject/{subject_id}")
async def marks_for_subject(subject_id: str, user=Depends(require_role("faculty", "admin"))):
    await assert_can_manage_subject(user, subject_id)
    records = await marks_collection.find({"subject_id": subject_id}).to_list(length=5000)
    return [{**r, "id": r["_id"]} for r in records]


@router.get("/mine")
async def my_marks(user=Depends(require_role("student"))):
    student = await students_collection.find_one({"user_id": user["_id"]})
    if not student:
        raise HTTPException(404, "Student profile not found.")
    records = await marks_collection.find({"student_id": student["_id"], "published": True}).to_list(length=1000)
    subject_ids = [r["subject_id"] for r in records]
    subjects = await subjects_collection.find({"_id": {"$in": subject_ids}}).to_list(length=1000)
    subjects_by_id = {s["_id"]: s for s in subjects}
    return [
        {**r, "id": r["_id"], "subject_name": subjects_by_id.get(r["subject_id"], {}).get("name")}
        for r in records
    ]
