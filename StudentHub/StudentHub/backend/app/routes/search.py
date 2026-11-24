"""
routes/search.py
Global search (Ctrl+K). Results are scoped to what the logged-in role is
actually allowed to see — a student never gets another student's name back,
and only Admin can search the full student/faculty directory.
"""
from fastapi import APIRouter, Depends

from app.database import (
    students_collection, faculty_collection, users_collection, subjects_collection,
    assignments_collection, uploaded_notes_collection, timetable_collection,
)
from app.auth import get_current_user

router = APIRouter(prefix="/search", tags=["Global Search"])


async def _names(user_ids: list[str]) -> dict:
    users = await users_collection.find({"_id": {"$in": user_ids}}).to_list(length=5000)
    return {u["_id"]: u for u in users}


@router.get("")
async def global_search(q: str, user=Depends(get_current_user)):
    q = (q or "").strip()
    if len(q) < 2:
        return {"query": q, "results": []}
    needle = q.lower()
    results = []

    if user["role"] == "admin":
        students = await students_collection.find({}).to_list(length=5000)
        users_by_id = await _names([s["user_id"] for s in students])
        for s in students:
            name = users_by_id.get(s["user_id"], {}).get("full_name", "")
            if needle in name.lower() or needle in s["student_id"].lower():
                results.append({"type": "student", "label": name, "sublabel": f"Student ID {s['student_id']}", "link": "/admin/students"})

        faculty = await faculty_collection.find({}).to_list(length=1000)
        fac_users = await _names([f["user_id"] for f in faculty])
        for f in faculty:
            name = fac_users.get(f["user_id"], {}).get("full_name", "")
            if needle in name.lower() or needle in f["faculty_id"].lower():
                results.append({"type": "faculty", "label": name, "sublabel": f"Faculty ID {f['faculty_id']}", "link": "/admin/faculty"})

    subjects = await subjects_collection.find({}).to_list(length=2000)
    for s in subjects:
        if needle in s["name"].lower() or needle in s["code"].lower():
            results.append({"type": "subject", "label": s["name"], "sublabel": s["code"], "link": f"/{user['role']}/subjects" if user["role"] == "admin" else None})

    if user["role"] in ("faculty", "student"):
        assignments = await assignments_collection.find({}).to_list(length=2000)
        for a in assignments:
            if needle in a["title"].lower():
                link = "/student/assignments" if user["role"] == "student" else "/faculty/assignments"
                results.append({"type": "assignment", "label": a["title"], "sublabel": f"Due {a['due_date']}", "link": link})

        notes = await uploaded_notes_collection.find({}).to_list(length=2000)
        for n in notes:
            if needle in (n.get("title") or "").lower():
                link = "/student/notes" if user["role"] == "student" else "/faculty/notes"
                results.append({"type": "note", "label": n["title"], "sublabel": f"Unit {n.get('unit', '')}", "link": link})

    if user["role"] == "admin":
        slots = await timetable_collection.find({}).to_list(length=2000)
        subj_by_id = {s["_id"]: s for s in subjects}
        for slot in slots:
            subj_name = subj_by_id.get(slot["subject_id"], {}).get("name", "")
            if needle in subj_name.lower() or needle in slot["classroom"].lower():
                results.append({"type": "timetable", "label": f"{subj_name} — {slot['day_of_week']}", "sublabel": f"{slot['start_time']}–{slot['end_time']} · {slot['classroom']}", "link": "/admin/timetable"})

    return {"query": q, "results": results[:30]}
