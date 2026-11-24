"""
routes/leave.py
Students (and faculty) apply for leave; Admin approves/rejects. Both
sides can view their own history.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from app.database import leave_requests_collection, users_collection
from app.auth import require_role, get_current_user
from app.models.leave import new_leave_document
from app.schemas.operations import ApplyLeaveRequest, ReviewLeaveRequest
from app.services.notifications import notify_user

router = APIRouter(prefix="/leave", tags=["Leave Management"])


@router.post("", status_code=201)
async def apply_leave(payload: ApplyLeaveRequest, user=Depends(require_role("student", "faculty"))):
    doc = new_leave_document(user["_id"], user["role"], payload.reason, payload.from_date, payload.to_date)
    await leave_requests_collection.insert_one(doc)

    admins = await users_collection.find({"role": "admin"}).to_list(length=100)
    for admin in admins:
        await notify_user(
            admin["_id"], "New Leave Request",
            f'{user["full_name"]} requested leave from {payload.from_date} to {payload.to_date}.',
            "leave_request", link="/admin/leave",
        )
    return {"message": "Leave request submitted successfully.", "id": doc["_id"]}


@router.get("/mine")
async def my_leave_history(user=Depends(require_role("student", "faculty"))):
    records = await leave_requests_collection.find({"user_id": user["_id"]}).sort("applied_at", -1).to_list(length=500)
    return [{**r, "id": r["_id"]} for r in records]


@router.get("")
async def all_leave_requests(status: str | None = None, admin=Depends(require_role("admin"))):
    query = {"status": status} if status else {}
    records = await leave_requests_collection.find(query).sort("applied_at", -1).to_list(length=1000)
    user_ids = [r["user_id"] for r in records]
    users = await users_collection.find({"_id": {"$in": user_ids}}).to_list(length=1000)
    users_by_id = {u["_id"]: u for u in users}
    return [
        {**r, "id": r["_id"], "full_name": users_by_id.get(r["user_id"], {}).get("full_name")}
        for r in records
    ]


@router.put("/{leave_id}/review")
async def review_leave(leave_id: str, payload: ReviewLeaveRequest, admin=Depends(require_role("admin"))):
    record = await leave_requests_collection.find_one({"_id": leave_id})
    if not record:
        raise HTTPException(404, "Leave request not found.")
    if record["status"] != "pending":
        raise HTTPException(400, "This leave request has already been reviewed.")

    await leave_requests_collection.update_one(
        {"_id": leave_id},
        {"$set": {"status": payload.status, "reviewed_by": admin["_id"], "reviewed_at": datetime.now(timezone.utc)}},
    )
    await notify_user(
        record["user_id"], f"Leave Request {payload.status.capitalize()}",
        f'Your leave request ({record["from_date"]} to {record["to_date"]}) was {payload.status}.',
        "leave_status",
    )
    return {"message": f"Leave request {payload.status}."}
