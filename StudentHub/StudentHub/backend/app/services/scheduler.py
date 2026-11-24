"""
services/scheduler.py
A background loop (started once in main.py's startup event — no external cron
needed) that runs every few minutes and sends the Smart Deadline Reminder alerts:
  - Blue:   assignment due in 3 days
  - Orange: assignment due tomorrow
  - Red:    assignment due today (and again when 6 hours remain)
It also publishes any announcement whose `scheduled_for` time has just arrived.
`alerts_collection` records exactly which (assignment_id, student_id, stage) or
(announcement_id,) combination has already been sent, so nobody is ever notified twice
for the same milestone even though this loop re-scans everything on every tick.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from app.database import (
    assignments_collection, subjects_collection, students_collection,
    submissions_collection, announcements_collection, alerts_collection,
)
from app.services.notifications import notify_user, notify_many
from app.utils.timeutil import local_now, today_str

CHECK_INTERVAL_SECONDS = 300  # 5 minutes — frequent enough for a live demo, cheap enough to leave running


async def _already_sent(key: str) -> bool:
    return await alerts_collection.find_one({"_id": key}) is not None


async def _mark_sent(key: str):
    await alerts_collection.insert_one({"_id": key, "sent_at": datetime.now(timezone.utc)})


async def _check_assignment_deadlines():
    now = local_now()
    today = now.date()
    assignments = await assignments_collection.find({}).to_list(length=5000)

    for a in assignments:
        due = datetime.fromisoformat(a["due_date"]).date()
        days_left = (due - today).days
        # Which milestone (if any) applies right now?
        if days_left == 3:
            stage, severity, phrase = "3_days", "blue", "is due in 3 days"
        elif days_left == 1:
            stage, severity, phrase = "tomorrow", "orange", "is due tomorrow"
        elif days_left == 0:
            hours_left = (datetime.combine(today, datetime.max.time().replace(microsecond=0), tzinfo=now.tzinfo) - now).total_seconds() / 3600
            stage = "due_today_6h" if hours_left <= 6 else "due_today"
            severity, phrase = "red", ("is due in under 6 hours" if stage == "due_today_6h" else "is due today")
        else:
            continue

        subject = await subjects_collection.find_one({"_id": a["subject_id"]})
        if not subject:
            continue
        students = await students_collection.find({"department": subject["department"], "semester": subject["semester"]}).to_list(length=5000)

        for s in students:
            submitted = await submissions_collection.find_one({"assignment_id": a["_id"], "student_id": s["_id"], "status": {"$in": ["submitted", "graded"]}})
            if submitted:
                continue
            key = f"deadline:{a['_id']}:{s['_id']}:{stage}"
            if await _already_sent(key):
                continue
            await notify_user(
                s["user_id"], f"{subject['name']} — {a['title']}", f'"{a["title"]}" {phrase}.',
                "assignment_reminder", severity=severity,
            )
            await _mark_sent(key)


async def _publish_scheduled_announcements():
    now_iso = local_now().isoformat()
    due = await announcements_collection.find({"scheduled_for": {"$ne": None, "$lte": now_iso}}).to_list(length=500)
    for ann in due:
        key = f"announcement:{ann['_id']}"
        if await _already_sent(key):
            continue
        students = await students_collection.find(
            {} if ann["target_type"] == "all" else
            ({"department": ann["department"]} if ann["target_type"] == "department" else {"department": ann["department"], "semester": ann["semester"]})
        ).to_list(length=10000)
        await notify_many([s["user_id"] for s in students], ann["title"], ann["message"], "new_announcement", link="/announcements")
        await _mark_sent(key)


async def run_scheduler_forever():
    while True:
        try:
            await _check_assignment_deadlines()
            await _publish_scheduled_announcements()
        except Exception as e:
            print(f"StudentHub scheduler warning: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
