"""
routes/skill_wallet.py
Student XP + badges. Faculty award XP for "helping others" or "event"; the
rest (attendance, submissions) is awarded automatically from other routes
via `award_xp()` below, which any route can import.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from app.database import skill_wallet_collection, students_collection
from app.auth import require_role, get_current_user
from app.models.skill_wallet import new_xp_document, XP_TABLE, BADGES
from app.services.notifications import notify_user

router = APIRouter(prefix="/skill-wallet", tags=["Skill Wallet"])


async def award_xp(user_id: str, activity: str, note: str | None = None):
    """Importable from any route: `await award_xp(student_user_id, "attendance")`. Silently
    no-ops for an unknown activity key so a typo never breaks the caller's real work."""
    xp = XP_TABLE.get(activity)
    if xp is None:
        return
    await skill_wallet_collection.insert_one(new_xp_document(user_id, activity, xp, note))


async def _summary(user_id: str) -> dict:
    entries = await skill_wallet_collection.find({"user_id": user_id}).sort("created_at", -1).to_list(length=2000)
    total_xp = sum(e["xp"] for e in entries)
    counts: dict = {}
    for e in entries:
        counts[e["activity"]] = counts.get(e["activity"], 0) + 1
    earned = [b for b in BADGES if b["check"](total_xp, counts)]
    level = total_xp // 100 + 1
    return {
        "total_xp": total_xp,
        "level": level,
        "xp_into_level": total_xp % 100,
        "xp_to_next_level": 100 - (total_xp % 100),
        "badges": [{"id": b["id"], "name": b["name"], "description": b["description"]} for b in earned],
        "recent": [{"activity": e["activity"], "xp": e["xp"], "note": e.get("note"), "created_at": e["created_at"]} for e in entries[:10]],
    }


@router.get("/me")
async def my_wallet(user=Depends(require_role("student"))):
    return await _summary(user["_id"])


class AwardXPRequest(BaseModel):
    student_id: str   # students collection _id
    activity: str
    note: str | None = None

    @field_validator("activity")
    @classmethod
    def v_activity(cls, v):
        if v not in ("event", "helping_others"):
            raise ValueError("Faculty can only award 'event' or 'helping_others' XP directly.")
        return v


@router.post("/award")
async def award(payload: AwardXPRequest, user=Depends(require_role("faculty", "admin"))):
    student = await students_collection.find_one({"_id": payload.student_id})
    if not student:
        raise HTTPException(404, "Student not found.")
    await award_xp(student["user_id"], payload.activity, payload.note)
    await notify_user(student["user_id"], "XP Awarded!", f"You earned {XP_TABLE[payload.activity]} XP" + (f" — {payload.note}" if payload.note else "."), "system_alert")
    return {"message": "XP awarded."}
