"""
routes/time_capsule.py
Students write a message to their future self and pick an unlock date (e.g.
"open before Semester 8"). The message content stays hidden from the API
response until unlock_date has arrived — no client-side trust required.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from datetime import datetime, timezone

from app.database import time_capsule_collection
from app.auth import require_role
from app.models.time_capsule import new_capsule_document
from app.utils.dates import reject_past_date
from app.utils.timeutil import today_str

router = APIRouter(prefix="/time-capsule", tags=["Time Capsule"])


class CreateCapsuleRequest(BaseModel):
    title: str
    message: str
    unlock_date: str

    @field_validator("title")
    @classmethod
    def v_title(cls, v):
        if not v.strip():
            raise ValueError("Title is required.")
        return v.strip()

    @field_validator("message")
    @classmethod
    def v_message(cls, v):
        if not v.strip():
            raise ValueError("Message is required.")
        return v.strip()

    @field_validator("unlock_date")
    @classmethod
    def v_unlock(cls, v):
        err = reject_past_date(v, "Unlock date")
        if err:
            raise ValueError(err)
        return v


def _serialize(c: dict) -> dict:
    is_unlocked = c["unlock_date"] <= today_str()
    return {
        "id": c["_id"],
        "title": c["title"],
        "unlock_date": c["unlock_date"],
        "is_unlocked": is_unlocked,
        # The message is withheld from the payload entirely until unlock — not just hidden by the UI.
        "message": c["message"] if is_unlocked else None,
        "created_at": c["created_at"],
    }


@router.post("", status_code=201)
async def create_capsule(payload: CreateCapsuleRequest, user=Depends(require_role("student"))):
    doc = new_capsule_document(user["_id"], payload.title, payload.message, payload.unlock_date)
    await time_capsule_collection.insert_one(doc)
    return {"message": "Time capsule scheduled.", "id": doc["_id"]}


@router.get("")
async def list_capsules(user=Depends(require_role("student"))):
    capsules = await time_capsule_collection.find({"user_id": user["_id"]}).sort("unlock_date", 1).to_list(length=500)
    return [_serialize(c) for c in capsules]


@router.delete("/{capsule_id}")
async def delete_capsule(capsule_id: str, user=Depends(require_role("student"))):
    result = await time_capsule_collection.delete_one({"_id": capsule_id, "user_id": user["_id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Time capsule not found.")
    return {"message": "Time capsule deleted."}
