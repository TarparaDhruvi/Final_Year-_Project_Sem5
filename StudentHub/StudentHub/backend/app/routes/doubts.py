"""
routes/doubts.py
Anonymous Doubt Wall. Students ask a question against a subject without their
identity ever being exposed to other students or faculty in the API response
(`asked_by_user_id` is stored for moderation but stripped before serializing).
Faculty reply publicly; the most-upvoted doubts sort first.
"""
from app.services.faculty_subject_links import is_assigned, faculty_ids_for_subject
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from app.database import doubts_collection, subjects_collection, faculty_collection, students_collection
from app.auth import require_role, get_current_user
from app.models.doubt import new_doubt_document
from app.services.notifications import notify_user

router = APIRouter(prefix="/doubts", tags=["Doubt Wall"])


class AskDoubtRequest(BaseModel):
    subject_id: str
    question: str

    @field_validator("question")
    @classmethod
    def v_question(cls, v):
        if not v.strip():
            raise ValueError("Please write your question.")
        if len(v) > 2000:
            raise ValueError("Question is too long (max 2000 characters).")
        return v.strip()


class ReplyRequest(BaseModel):
    reply: str

    @field_validator("reply")
    @classmethod
    def v_reply(cls, v):
        if not v.strip():
            raise ValueError("Reply cannot be empty.")
        return v.strip()


def _serialize(d: dict, user_id: str) -> dict:
    """Never includes asked_by_user_id — that's the whole point of 'anonymous'."""
    return {
        "id": d["_id"],
        "subject_id": d["subject_id"],
        "question": d["question"],
        "reply": d.get("reply"),
        "replied_at": d.get("replied_at"),
        "upvotes": len(d.get("upvoted_by", [])),
        "has_upvoted": user_id in d.get("upvoted_by", []),
        "is_mine": d["asked_by_user_id"] == user_id,   # lets the asker see "your question" without naming them to anyone else
        "created_at": d["created_at"],
    }


@router.post("", status_code=201)
async def ask_doubt(payload: AskDoubtRequest, user=Depends(require_role("student"))):
    subject = await subjects_collection.find_one({"_id": payload.subject_id})
    if not subject:
        raise HTTPException(404, "Subject not found.")

    doc = new_doubt_document(payload.subject_id, user["_id"], payload.question)
    await doubts_collection.insert_one(doc)

    for fid in await faculty_ids_for_subject(payload.subject_id):   # every teacher of the subject is notified
        faculty = await faculty_collection.find_one({"faculty_id": fid})
        if faculty:
            await notify_user(faculty["user_id"], "New Anonymous Doubt", f'A student asked a question in {subject["name"]}.', "new_doubt")
    return {"message": "Your question was posted anonymously.", "id": doc["_id"]}


@router.get("/subject/{subject_id}")
async def list_doubts(subject_id: str, user=Depends(require_role("student", "faculty", "admin"))):
    doubts = await doubts_collection.find({"subject_id": subject_id}).to_list(length=1000)
    doubts.sort(key=lambda d: (-len(d.get("upvoted_by", [])), d["created_at"]))
    return [_serialize(d, user["_id"]) for d in doubts]


@router.post("/{doubt_id}/upvote")
async def upvote(doubt_id: str, user=Depends(require_role("student", "faculty"))):
    doubt = await doubts_collection.find_one({"_id": doubt_id})
    if not doubt:
        raise HTTPException(404, "Doubt not found.")
    if user["_id"] in doubt.get("upvoted_by", []):
        await doubts_collection.update_one({"_id": doubt_id}, {"$pull": {"upvoted_by": user["_id"]}})
        return {"message": "Upvote removed.", "upvoted": False}
    await doubts_collection.update_one({"_id": doubt_id}, {"$addToSet": {"upvoted_by": user["_id"]}})
    return {"message": "Upvoted.", "upvoted": True}


@router.put("/{doubt_id}/reply")
async def reply_doubt(doubt_id: str, payload: ReplyRequest, user=Depends(require_role("faculty"))):
    doubt = await doubts_collection.find_one({"_id": doubt_id})
    if not doubt:
        raise HTTPException(404, "Doubt not found.")
    subject = await subjects_collection.find_one({"_id": doubt["subject_id"]})
    faculty = await faculty_collection.find_one({"user_id": user["_id"]})
    if not subject or not faculty or not await is_assigned(faculty["faculty_id"], doubt["subject_id"]):
        raise HTTPException(403, "You are not assigned to this subject.")

    from datetime import datetime, timezone
    await doubts_collection.update_one(
        {"_id": doubt_id},
        {"$set": {"reply": payload.reply, "replied_by": user["_id"], "replied_at": datetime.now(timezone.utc)}},
    )

    student = await students_collection.find_one({"user_id": doubt["asked_by_user_id"]})
    if student:
        await notify_user(student["user_id"], "Your Doubt Was Answered", f'{subject["name"]}: {payload.reply[:80]}', "new_doubt", link="/doubts")
    return {"message": "Reply posted."}
