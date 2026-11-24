"""
routes/faculty_students.py
Faculty student management. A faculty member can only see and act on students ENROLLED in a subject the
Admin assigned to them (same department + semester as that subject) — enforced here on the server for
every request, not just by what the UI shows.

  GET  /faculty/me/students                list / search / filter my students
  GET  /faculty/me/students/{id}           profile + attendance / marks / assignments for MY subjects only
  PUT  /faculty/me/students/{id}           permitted profile edits: phone and batch only

Academic operations (mark attendance, enter/publish marks, grade assignments) reuse the existing
/attendance, /marks and /assignments endpoints, which apply the same ownership + enrolment checks.
Everything reads/writes the same MongoDB collections the Admin and Student portals use, so a change made
here shows up there immediately. Admin keeps institution-wide access via /students.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.database import users_collection, students_collection, attendance_collection, marks_collection
from app.auth import require_role
from app.schemas.academic import FacultyStudentEditRequest
from app.services.access import faculty_student_scope, is_enrolled
from app.services.student_records import academic_record

router = APIRouter(prefix="/faculty/me/students", tags=["Faculty Student Management"])


async def _in_scope_student(user: dict, student_doc_id: str) -> tuple[dict, list[dict]]:
    """(student, my subjects that student is enrolled in). 404 for unknown id, 403 if not one of my students."""
    student = await students_collection.find_one({"_id": student_doc_id})
    if not student:
        raise HTTPException(404, "Student not found.")
    subjects, _ = await faculty_student_scope(user)
    shared = [s for s in subjects if is_enrolled(student, s)]
    if not shared:
        raise HTTPException(403, "This student is not in any of your assigned subjects.")
    return student, shared


@router.get("")
async def my_students(
    search: Optional[str] = None,
    department: Optional[str] = None,
    semester: Optional[int] = None,
    subject_id: Optional[str] = None,
    user=Depends(require_role("faculty")),
):
    subjects, scope = await faculty_student_scope(user)
    if subject_id:
        chosen = next((s for s in subjects if s["_id"] == subject_id), None)
        if not chosen:
            raise HTTPException(403, "You are not assigned to this subject.")
        scope = {"department": chosen["department"], "semester": chosen["semester"]}

    query = {"$and": [scope]}
    if department:
        query["$and"].append({"department": department})
    if semester:
        query["$and"].append({"semester": semester})
    students = await students_collection.find(query).sort("student_id", 1).to_list(length=5000)

    users = await users_collection.find({"_id": {"$in": [s["user_id"] for s in students]}}).to_list(length=5000)
    users_by_id = {u["_id"]: u for u in users}

    # Aggregate attendance across MY subjects only.
    my_subject_ids = [s["_id"] for s in subjects]
    att = await attendance_collection.find(
        {"student_id": {"$in": [s["_id"] for s in students]}, "subject_id": {"$in": my_subject_ids}}).to_list(length=100000)
    att_by_student: dict = {}
    for r in att:
        c = att_by_student.setdefault(r["student_id"], {"present": 0, "total": 0})
        c["total"] += 1
        c["present"] += 1 if r["status"] == "present" else 0

    needle = (search or "").strip().lower()
    out = []
    for s in students:
        u = users_by_id.get(s["user_id"], {})
        if needle and not any(needle in str(v or "").lower() for v in (u.get("full_name"), s["student_id"], u.get("email"), u.get("phone"))):
            continue
        shared = [sub for sub in subjects if is_enrolled(s, sub)]
        c = att_by_student.get(s["_id"], {"present": 0, "total": 0})
        out.append({
            "id": s["_id"], "student_id": s["student_id"], "full_name": u.get("full_name"), "email": u.get("email"),
            "phone": u.get("phone"), "department": s["department"], "semester": s["semester"], "batch": s.get("batch"),
            "is_active": u.get("is_active", True),
            "subjects": [{"id": sub["_id"], "name": sub["name"]} for sub in shared],
            "attendance_percentage": round(c["present"] / c["total"] * 100, 1) if c["total"] else None,
        })
    return out


@router.get("/{student_doc_id}")
async def my_student_detail(student_doc_id: str, user=Depends(require_role("faculty"))):
    student, shared_subjects = await _in_scope_student(user, student_doc_id)
    u = await users_collection.find_one({"_id": student["user_id"]}) or {}
    return {
        "id": student["_id"], "student_id": student["student_id"], "full_name": u.get("full_name"), "email": u.get("email"),
        "phone": u.get("phone"), "department": student["department"], "semester": student["semester"],
        "batch": student.get("batch"), "is_active": u.get("is_active", True),
        "academics": await academic_record(student, shared_subjects),
    }


@router.put("/{student_doc_id}")
async def edit_my_student(student_doc_id: str, payload: FacultyStudentEditRequest, user=Depends(require_role("faculty"))):
    student, _ = await _in_scope_student(user, student_doc_id)
    sent = payload.model_fields_set
    now = datetime.now(timezone.utc)
    if "phone" not in sent and "batch" not in sent:
        raise HTTPException(400, "Nothing to update. Faculty can edit phone and batch only.")
    if "phone" in sent and payload.phone:
        await users_collection.update_one({"_id": student["user_id"]}, {"$set": {"phone": payload.phone, "updated_at": now}})
    if "batch" in sent:
        await students_collection.update_one({"_id": student["_id"]}, {"$set": {"batch": payload.batch or None, "updated_at": now}})
    return {"message": "Student updated."}
