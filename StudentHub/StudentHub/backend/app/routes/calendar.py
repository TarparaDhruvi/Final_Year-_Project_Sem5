"""
routes/calendar.py
Smart Calendar: merges assignment due dates, leave, AI Study Coach exam dates
+ planner sessions, and timetable classes into one unified, role-scoped feed —
read-only; each item's own module (Assignments, Leave, Study Coach...) is
still where you'd actually act on it.
"""
from fastapi import APIRouter, Depends

from app.database import (
    assignments_collection, subjects_collection, leave_requests_collection,
    students_collection, faculty_collection, study_plans_collection, timetable_collection,
)
from app.auth import require_role

router = APIRouter(prefix="/calendar", tags=["Smart Calendar"])

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@router.get("/me")
async def my_calendar(user=Depends(require_role("student", "faculty", "admin"))):
    """`events` are dated items (assignment deadlines, exams, study sessions, leave). `weekly_classes` are the
    user's recurring timetable lectures (day_of_week + times); the client places them on each matching date.
    Both come from the same scoped sources as the rest of the app — nothing is invented."""
    events = []
    weekly_classes = []
    if user["role"] in ("student", "faculty"):
        from app.routes.timetable import schedule_slots_for_user
        weekly_classes = await schedule_slots_for_user(user)

    if user["role"] == "student":
        student = await students_collection.find_one({"user_id": user["_id"]})
        if student:
            subjects = await subjects_collection.find({"department": student["department"], "semester": student["semester"]}).to_list(length=200)
            subj_by_id = {s["_id"]: s for s in subjects}
            assignments = await assignments_collection.find({"subject_id": {"$in": list(subj_by_id.keys())}}).to_list(length=1000)
            for a in assignments:
                events.append({"date": a["due_date"], "type": "assignment", "title": a["title"], "detail": subj_by_id.get(a["subject_id"], {}).get("name", "")})

        plans = await study_plans_collection.find({"user_id": user["_id"]}).to_list(length=200)
        for p in plans:
            events.append({"date": p["exam_date"], "type": "exam", "title": f"Exam — {p['subject']}", "detail": "From your AI Study Coach plan"})
            for d in p.get("planner", []):
                events.append({"date": d["date"], "type": "study_session", "title": f"Study: {d['focus_topic']}", "detail": f"{d['target_hours']}h target"})

    elif user["role"] == "faculty":
        faculty = await faculty_collection.find_one({"user_id": user["_id"]})
        if faculty:
            from app.services.faculty_subject_links import subjects_for_faculty
            subjects = await subjects_for_faculty(faculty["faculty_id"])
            subj_by_id = {s["_id"]: s for s in subjects}
            assignments = await assignments_collection.find({"subject_id": {"$in": list(subj_by_id.keys())}}).to_list(length=1000)
            for a in assignments:
                events.append({"date": a["due_date"], "type": "assignment", "title": f"Due: {a['title']}", "detail": subj_by_id.get(a["subject_id"], {}).get("name", "")})

    leave_query = {"user_id": user["_id"]} if user["role"] != "admin" else {"status": "approved"}
    leaves = await leave_requests_collection.find(leave_query).to_list(length=500)
    for l in leaves:
        if user["role"] == "admin" or l["status"] == "approved":
            events.append({"date": l["from_date"], "end_date": l.get("to_date") or l["from_date"], "type": "leave",
                           "title": "Leave" if user["role"] == "admin" else "Your leave", "detail": f"{l['from_date']} to {l['to_date']}"})

    events.sort(key=lambda e: e["date"])
    return {"events": events, "weekly_classes": weekly_classes}
