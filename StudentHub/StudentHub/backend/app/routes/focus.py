"""
routes/focus.py
Focus Mode: a timed, distraction-free study session the frontend renders as a
full-screen timer. The backend just tracks start/stop so "Study Streak" and
total focus minutes on the dashboard are built from real sessions, not guesses.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import study_sessions_collection
from app.auth import require_role
from app.models.study_session import new_session_document

router = APIRouter(prefix="/focus", tags=["Focus Mode"])


class StartSessionRequest(BaseModel):
    subject_id: str | None = None
    goal_minutes: int = 25


@router.post("/start")
async def start_session(payload: StartSessionRequest, user=Depends(require_role("student"))):
    active = await study_sessions_collection.find_one({"user_id": user["_id"], "ended_at": None})
    if active:
        raise HTTPException(409, "You already have an active study session.")
    doc = new_session_document(user["_id"], payload.subject_id, max(1, min(payload.goal_minutes, 180)))
    await study_sessions_collection.insert_one(doc)
    return {"id": doc["_id"], "goal_minutes": doc["goal_minutes"], "started_at": doc["started_at"]}


@router.post("/{session_id}/end")
async def end_session(session_id: str, user=Depends(require_role("student"))):
    session = await study_sessions_collection.find_one({"_id": session_id, "user_id": user["_id"]})
    if not session:
        raise HTTPException(404, "Session not found.")
    if session["ended_at"]:
        raise HTTPException(400, "This session has already ended.")

    now = datetime.now(timezone.utc)
    started = session["started_at"].replace(tzinfo=timezone.utc) if session["started_at"].tzinfo is None else session["started_at"]
    minutes = round((now - started).total_seconds() / 60, 1)
    completed = minutes >= session["goal_minutes"]
    await study_sessions_collection.update_one({"_id": session_id}, {"$set": {"ended_at": now, "actual_minutes": minutes, "completed": completed}})
    return {"actual_minutes": minutes, "completed": completed}


@router.get("/stats")
async def focus_stats(user=Depends(require_role("student"))):
    sessions = await study_sessions_collection.find({"user_id": user["_id"], "ended_at": {"$ne": None}}).sort("started_at", -1).to_list(length=1000)
    total_minutes = sum(s["actual_minutes"] or 0 for s in sessions)

    # Study streak: consecutive days (including today or yesterday) with at least one completed session.
    days_with_session = sorted({s["started_at"].date() for s in sessions if s["completed"]}, reverse=True)
    streak = 0
    if days_with_session:
        cursor = datetime.now(timezone.utc).date()
        for d in days_with_session:
            if d == cursor or d == cursor - timedelta(days=1):
                streak += 1
                cursor = d - timedelta(days=1)
            else:
                break

    return {
        "total_sessions": len(sessions), "total_minutes": round(total_minutes), "streak_days": streak,
        "recent": [{"id": s["_id"], "minutes": s["actual_minutes"], "completed": s["completed"], "started_at": s["started_at"]} for s in sessions[:10]],
    }
