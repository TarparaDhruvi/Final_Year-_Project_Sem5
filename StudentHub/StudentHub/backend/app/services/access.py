"""
services/access.py
One place for "may this user act on this subject / this student?" so every route enforces the same
rules instead of re-implementing them (and forgetting one).

  * Admin: institution-wide — may act on any subject and any student.
  * Faculty: only on subjects the Admin assigned to them (a (faculty_id, subject_id) pair in `faculty_subjects`; a subject may have many teachers),
    and only on students ENROLLED in such a subject (same department + semester as the subject).
  * Student: never reaches these helpers' write paths.
"""
from fastapi import HTTPException

from app.database import faculty_collection, subjects_collection, students_collection
from app.services.faculty_subject_links import subjects_for_faculty, is_assigned


async def faculty_profile(user: dict) -> dict | None:
    return await faculty_collection.find_one({"user_id": user["_id"]})


async def faculty_subjects(user: dict) -> list[dict]:
    faculty = await faculty_profile(user)
    if not faculty:
        return []
    return await subjects_for_faculty(faculty["faculty_id"])


async def assert_can_manage_subject(user: dict, subject_id: str) -> dict:
    """Returns the subject. Raises 404 if it doesn't exist, 403 if a faculty member isn't assigned to it."""
    subject = await subjects_collection.find_one({"_id": subject_id})
    if not subject:
        raise HTTPException(404, "Subject not found.")
    if user["role"] == "admin":
        return subject
    faculty = await faculty_profile(user)
    if user["role"] != "faculty" or not faculty or not await is_assigned(faculty["faculty_id"], subject_id):
        raise HTTPException(403, "You are not assigned to this subject.")
    return subject


def is_enrolled(student: dict, subject: dict) -> bool:
    return student.get("department") == subject.get("department") and student.get("semester") == subject.get("semester")


async def assert_students_enrolled(student_ids: list[str], subject: dict) -> dict:
    """All `student_ids` (students-collection _ids) must exist and be enrolled in `subject`. Returns {id: student}."""
    wanted = list(dict.fromkeys(student_ids))
    found = await students_collection.find({"_id": {"$in": wanted}}).to_list(length=5000)
    by_id = {s["_id"]: s for s in found}
    missing = [sid for sid in wanted if sid not in by_id]
    if missing:
        raise HTTPException(404, "One or more students were not found.")
    not_enrolled = [s for s in found if not is_enrolled(s, subject)]
    if not_enrolled:
        raise HTTPException(403, "One or more students are not enrolled in this subject.")
    return by_id


async def faculty_student_scope(user: dict) -> tuple[list[dict], dict]:
    """(subjects, mongo_filter) describing every student a faculty member may see: the union of
    (department, semester) pairs of their assigned subjects. Empty subjects -> filter matching nobody."""
    subjects = await faculty_subjects(user)
    pairs = {(s["department"], s["semester"]) for s in subjects}
    if not pairs:
        return subjects, {"_id": {"$in": []}}
    return subjects, {"$or": [{"department": d, "semester": sem} for d, sem in pairs]}
