"""
services/notifications.py
Single choke point for creating a notification: writes it to Mongo AND
pushes it live over the user's WebSocket connection (if they're online).
Every route that needs to notify a user (leave approved, new assignment,
new announcement, new submission...) calls notify_user() instead of
touching notifications_collection or the websocket manager directly.
"""

import uuid
from datetime import datetime, timezone

from app.database import notifications_collection
from app.websocket import manager

NOTIFICATION_TYPES = (
    "assignment_reminder",
    "missed_deadline",
    "new_note",
    "new_announcement",
    "leave_status",
    "study_reminder",
    "new_submission",
    "leave_request",
    "new_doubt",
    "timetable_update",
    "faculty_request",
    "system_alert",
)


async def notify_user(user_id: str, title: str, message: str, notif_type: str, link: str | None = None, severity: str | None = None):
    doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": title,
        "message": message,
        "type": notif_type,
        "link": link,
        "severity": severity,          # blue | orange | red (deadline colour system)
        "is_read": False,
        "created_at": datetime.now(timezone.utc),
    }
    await notifications_collection.insert_one(doc)

    # Push live if the user has an open WebSocket connection; if they
    # don't, they'll simply see it in the notification bell on next login.
    await manager.send_to_user(
        user_id,
        {
            "event": "notification",
            "notification": {
                "id": doc["_id"],
                "title": title,
                "message": message,
                "type": notif_type,
                "link": link,
                "severity": severity,
                "is_read": False,
                "created_at": doc["created_at"].isoformat(),
            },
        },
    )
    return doc


async def notify_many(user_ids: list[str], title: str, message: str, notif_type: str, link: str | None = None, severity: str | None = None):
    for uid in user_ids:
        await notify_user(uid, title, message, notif_type, link, severity)
