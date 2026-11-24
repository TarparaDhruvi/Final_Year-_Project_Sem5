"""
services/student_records.py
Builds one student's academic record (attendance %, marks, assignment status) from the existing
collections — nothing is copied or duplicated. Used by the Admin student profile (all subjects of the
student's class) and by the Faculty student view (ONLY the subjects that faculty member teaches), so
both portals always show the same live MongoDB data.
"""
from app.database import (
    attendance_collection, marks_collection, assignments_collection, submissions_collection, faculty_collection, users_collection,
    faculty_subjects_collection,
)


async def academic_record(student: dict, subjects: list[dict]) -> list[dict]:
    if not subjects:
        return []
    subject_ids = [s["_id"] for s in subjects]
    sid = student["_id"]

    attendance = await attendance_collection.find({"student_id": sid, "subject_id": {"$in": subject_ids}}).to_list(length=20000)
    marks = await marks_collection.find({"student_id": sid, "subject_id": {"$in": subject_ids}}).to_list(length=1000)
    assignments = await assignments_collection.find({"subject_id": {"$in": subject_ids}}).sort("due_date", 1).to_list(length=2000)
    submissions = await submissions_collection.find(
        {"student_id": sid, "assignment_id": {"$in": [a["_id"] for a in assignments]}}).to_list(length=2000)

    teacher_links = await faculty_subjects_collection.find({"subject_id": {"$in": subject_ids}}).to_list(length=20000)
    teachers_of: dict = {}
    for l in teacher_links:
        teachers_of.setdefault(l["subject_id"], []).append(l["faculty_id"])
    faculty_docs = await faculty_collection.find({"faculty_id": {"$in": list({l["faculty_id"] for l in teacher_links})}}).to_list(length=500)
    fac_users = {u["_id"]: u for u in await users_collection.find({"_id": {"$in": [f["user_id"] for f in faculty_docs]}}).to_list(length=500)}
    faculty_name = {f["faculty_id"]: fac_users.get(f["user_id"], {}).get("full_name") for f in faculty_docs}

    att_by_subject: dict = {}
    for r in attendance:
        c = att_by_subject.setdefault(r["subject_id"], {"present": 0, "total": 0})
        c["total"] += 1
        c["present"] += 1 if r["status"] == "present" else 0
    marks_by_subject = {m["subject_id"]: m for m in marks}
    sub_by_assignment = {s["assignment_id"]: s for s in submissions}

    rows = []
    for subj in subjects:
        c = att_by_subject.get(subj["_id"], {"present": 0, "total": 0})
        pct = round(c["present"] / c["total"] * 100, 1) if c["total"] else None
        m = marks_by_subject.get(subj["_id"])
        rows.append({
            "subject_id": subj["_id"], "subject_name": subj["name"], "subject_code": subj.get("code"),
            "faculty_ids": teachers_of.get(subj["_id"], []),
            "faculty_name": ", ".join(n for n in (faculty_name.get(f) for f in teachers_of.get(subj["_id"], [])) if n) or None,
            "attendance": {"present": c["present"], "total": c["total"], "percentage": pct, "at_risk": pct is not None and pct < 75},
            "marks": ({"id": m["_id"], "internal": m.get("internal"), "practical": m.get("practical"), "published": bool(m.get("published"))} if m else None),
            "assignments": [
                {
                    "id": a["_id"], "title": a["title"], "due_date": a["due_date"],
                    "status": sub_by_assignment[a["_id"]]["status"] if a["_id"] in sub_by_assignment else "not_submitted",
                    "submission_id": sub_by_assignment[a["_id"]]["_id"] if a["_id"] in sub_by_assignment else None,
                    "grade": sub_by_assignment[a["_id"]].get("grade") if a["_id"] in sub_by_assignment else None,
                    "feedback": sub_by_assignment[a["_id"]].get("feedback") if a["_id"] in sub_by_assignment else None,
                    "file_url": sub_by_assignment[a["_id"]].get("file_url") if a["_id"] in sub_by_assignment else None,
                }
                for a in assignments if a["subject_id"] == subj["_id"]
            ],
        })
    return rows
