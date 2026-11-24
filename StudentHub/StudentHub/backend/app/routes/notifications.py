"""
routes/notifications.py
Powers the notification bell for every role: list (paginated-ish via
limit), unread count, mark one as read, mark all as read.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.database import notifications_collection
from app.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(limit: int = 30, user=Depends(get_current_user)):
    records = await notifications_collection.find({"user_id": user["_id"]}).sort("created_at", -1).to_list(length=limit)
    return [{**r, "id": r["_id"]} for r in records]


@router.get("/unread-count")
async def unread_count(user=Depends(get_current_user)):
    count = await notifications_collection.count_documents({"user_id": user["_id"], "is_read": False})
    return {"count": count}


@router.put("/{notification_id}/read")
async def mark_read(notification_id: str, user=Depends(get_current_user)):
    result = await notifications_collection.update_one(
        {"_id": notification_id, "user_id": user["_id"]}, {"$set": {"is_read": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Notification not found.")
    return {"message": "Marked as read."}


@router.put("/read-all")
async def mark_all_read(user=Depends(get_current_user)):
    await notifications_collection.update_many({"user_id": user["_id"], "is_read": False}, {"$set": {"is_read": True}})
    return {"message": "All notifications marked as read."}
