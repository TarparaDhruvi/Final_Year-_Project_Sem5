"""
routes/activity_hub.py — Faculty "Classroom Activity Hub"

One read-only call that powers the Faculty dashboard's daily teaching view: today's classes, the work that is
actually outstanding, and a workload summary. Every figure is computed from MongoDB at request time and is
scoped to the subjects the Admin has CURRENTLY assigned to the logged-in faculty member — another faculty
member's classes, students and records can never appear (the endpoint is faculty-only and every query is
filtered by that member's assigned subject IDs).

Definitions (so each number can be audited):
  * Today's classes ........ timetable slots for today's weekday, for subjects the faculty member teaches now.
  * Lecture n of m ......... the slot's position in today's order (the timetable stores no lecture numbers).
  * Attendance status ...... per SUBJECT and today's date (attendance is stored per subject/date, not per slot):
                             complete = every enrolled student marked, partial = some, pending = none.
  * Task: attendance ....... subjects with a class that has already started today and attendance not complete.
  * Task: marks to enter ... enrolled students with no internal/practical mark recorded for a subject.
  * Task: marks to publish . recorded marks that are not yet published.
  * Task: submissions ...... student submissions with status "submitted" (handed in, not yet graded).
  * Task: doubts ........... Doubt Wall questions in the faculty member's subjects that have no reply.
  * Enrolled ............... students whose department + semester match the subject (same rule as attendance/marks).
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends

from app.database import (
    students_collection, attendance_collection, marks_collection, assignments_collection, submissions_collection,
    uploaded_notes_collection, doubts_collection,
)
from app.auth import require_role
from app.utils.timeutil import local_now
from app.services.access import faculty_subjects, is_enrolled
from app.routes.timetable import schedule_slots_for_user

router = APIRouter(prefix="/faculty/me", tags=["Faculty Classroom Activity Hub"])

_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _breakdown(counts: dict, names: dict, limit: int = 5) -> list[dict]:
    rows = [{"subject_id": sid, "subject_name": names.get(sid, "Subject"), "count": c} for sid, c in counts.items() if c > 0]
    return sorted(rows, key=lambda r: (-r["count"], r["subject_name"]))[:limit]


@router.get("/activity-hub")
async def activity_hub(user=Depends(require_role("faculty"))):
    now: datetime = local_now()
    today_iso = now.date().isoformat()
    weekday = _WEEKDAYS[now.weekday()]
    now_minutes = now.hour * 60 + now.minute

    subjects = await faculty_subjects(user)               # ONLY subjects currently assigned to this faculty member
    names = {s["_id"]: s["name"] for s in subjects}
    subject_ids = list(names)

    # ---- enrolled students per subject (department + semester), one query per distinct class group
    groups = {(s["department"], s["semester"]) for s in subjects}
    students_by_group: dict = {}
    for dept, sem in groups:
        students_by_group[(dept, sem)] = await students_collection.find({"department": dept, "semester": sem}).to_list(length=20000)
    enrolled_ids = {s["_id"]: {st["_id"] for st in students_by_group[(s["department"], s["semester"])]} for s in subjects}

    # ---- today's attendance, per subject
    att_today = await attendance_collection.find({"subject_id": {"$in": subject_ids}, "date": today_iso}).to_list(length=100000) if subject_ids else []
    marked_by_subject: dict = {}
    for r in att_today:
        if r["student_id"] in enrolled_ids.get(r["subject_id"], set()):
            marked_by_subject.setdefault(r["subject_id"], set()).add(r["student_id"])

    def attendance_state(subject_id: str) -> dict:
        enrolled, marked = len(enrolled_ids.get(subject_id, ())), len(marked_by_subject.get(subject_id, ()))
        if enrolled == 0:
            status = "no_students"
        elif marked >= enrolled:
            status = "complete"
        elif marked > 0:
            status = "partial"
        else:
            status = "pending"
        return {"status": status, "marked": marked, "enrolled": enrolled}

    # ---- per-subject readiness inputs
    assignments = await assignments_collection.find({"subject_id": {"$in": subject_ids}}).to_list(length=20000) if subject_ids else []
    assignment_subject = {a["_id"]: a["subject_id"] for a in assignments}
    open_assignments: dict = {}
    for a in assignments:
        if a["due_date"] >= today_iso:
            open_assignments[a["subject_id"]] = open_assignments.get(a["subject_id"], 0) + 1
    notes = await uploaded_notes_collection.find({"subject_id": {"$in": subject_ids}}).to_list(length=50000) if subject_ids else []
    notes_count: dict = {}
    for n in notes:
        notes_count[n["subject_id"]] = notes_count.get(n["subject_id"], 0) + 1
    submissions = await submissions_collection.find(
        {"assignment_id": {"$in": list(assignment_subject)}, "status": "submitted"}).to_list(length=100000) if assignment_subject else []
    to_review: dict = {}
    for sub in submissions:
        sid = assignment_subject[sub["assignment_id"]]
        to_review[sid] = to_review.get(sid, 0) + 1

    # ---- today's classes
    slots = [s for s in await schedule_slots_for_user(user) if s["day_of_week"] == weekday]
    slots.sort(key=lambda s: s["start_time"])
    classes = []
    for i, s in enumerate(slots):
        sid = s["subject_id"]
        att = attendance_state(sid)
        classes.append({
            "slot_id": s["id"], "lecture": i + 1, "lectures_today": len(slots),
            "subject_id": sid, "subject_name": s["subject_name"], "subject_code": s.get("subject_code"),
            "start_time": s["start_time"], "end_time": s["end_time"], "classroom": s["classroom"],
            "department": s["department"], "semester": s["semester"],
            "enrolled_students": att["enrolled"],
            "attendance": att,
            "readiness": {"notes_uploaded": notes_count.get(sid, 0), "open_assignments": open_assignments.get(sid, 0), "submissions_to_review": to_review.get(sid, 0)},
            "started": now_minutes >= _minutes(s["start_time"]),
            "ended": now_minutes >= _minutes(s["end_time"]),
        })

    # ---- pending tasks
    attendance_pending: dict = {}
    for c in classes:
        if c["started"] and c["attendance"]["status"] in ("pending", "partial"):
            attendance_pending[c["subject_id"]] = 1
    marks_docs = await marks_collection.find({"subject_id": {"$in": subject_ids}}).to_list(length=200000) if subject_ids else []
    entered: dict = {}
    to_publish: dict = {}
    for m in marks_docs:
        if m["student_id"] not in enrolled_ids.get(m["subject_id"], set()):
            continue
        if m.get("internal") is not None or m.get("practical") is not None:
            entered.setdefault(m["subject_id"], set()).add(m["student_id"])
            if not m.get("published"):
                to_publish[m["subject_id"]] = to_publish.get(m["subject_id"], 0) + 1
    to_enter = {sid: max(0, len(enrolled_ids[sid]) - len(entered.get(sid, ()))) for sid in subject_ids}
    doubts = await doubts_collection.find({"subject_id": {"$in": subject_ids}, "reply": None}).to_list(length=50000) if subject_ids else []
    doubts_open: dict = {}
    for d in doubts:
        doubts_open[d["subject_id"]] = doubts_open.get(d["subject_id"], 0) + 1

    def task(key: str, label: str, counts: dict) -> dict:
        return {"key": key, "label": label, "count": sum(counts.values()), "breakdown": _breakdown(counts, names)}

    tasks = [
        task("attendance", "Attendance not marked", attendance_pending),
        task("marks_to_enter", "Marks to enter", to_enter),
        task("marks_to_publish", "Marks ready to publish", to_publish),
        task("submissions_to_review", "Submissions to review", to_review),
        task("doubts_unanswered", "Doubts awaiting a reply", doubts_open),
    ]

    # ---- workload summary (only things that can be calculated from the data)
    teaching_minutes = sum(max(0, _minutes(c["end_time"]) - _minutes(c["start_time"])) for c in classes)
    todays_students: set = set()
    for c in classes:
        todays_students |= enrolled_ids.get(c["subject_id"], set())
    week_end = (now.date() + timedelta(days=6)).isoformat()
    due_this_week = sum(1 for a in assignments if today_iso <= a["due_date"] <= week_end)
    started_subjects = {c["subject_id"] for c in classes if c["started"] and c["attendance"]["status"] != "no_students"}
    attendance_done = {sid for sid in started_subjects if attendance_state(sid)["status"] == "complete"}

    return {
        "date": today_iso, "weekday": weekday, "assigned_subjects": len(subjects),
        "classes": classes, "tasks": tasks,
        "summary": {
            "classes_today": len(classes), "teaching_minutes_today": teaching_minutes, "students_today": len(todays_students),
            "attendance_subjects_started": len(started_subjects), "attendance_subjects_done": len(attendance_done),
            "tasks_outstanding": sum(t["count"] for t in tasks), "assignments_due_this_week": due_this_week,
        },
    }
