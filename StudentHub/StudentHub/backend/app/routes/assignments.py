"""
routes/assignments.py
Faculty create assignments and grade submissions; students view, submit,
and track their submission status/history. Every submission keeps a
`timeline` (Assignment DNA) and creates/updates notifications so the
Smart Deadline Reminder system has real data to work from.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from app.database import (
    assignments_collection, submissions_collection, subjects_collection,
    faculty_collection, students_collection, users_collection,
)
from app.auth import require_role
from app.models.assignment import new_assignment_document
from app.models.submission import new_submission_document, timeline_event
from app.schemas.operations import CreateAssignmentRequest, SubmitAssignmentRequest, GradeSubmissionRequest
from app.services.notifications import notify_user, notify_many
from app.routes.skill_wallet import award_xp
from app.utils.timeutil import today_str
from app.services.access import assert_can_manage_subject, is_enrolled
from app.services.faculty_subject_links import is_assigned

router = APIRouter(prefix="/assignments", tags=["Assignments"])


@router.post("", status_code=201)
async def create_assignment(payload: CreateAssignmentRequest, user=Depends(require_role("faculty"))):
    faculty = await faculty_collection.find_one({"user_id": user["_id"]})
    subject = await subjects_collection.find_one({"_id": payload.subject_id})
    if not subject or not faculty or not await is_assigned(faculty["faculty_id"], payload.subject_id):
        raise HTTPException(403, "You are not assigned to this subject.")

    doc = new_assignment_document(
        title=payload.title, description=payload.description, subject_id=payload.subject_id,
        faculty_id=faculty["faculty_id"], due_date=payload.due_date,
        instructions_file_url=payload.instructions_file_url,
    )
    await assignments_collection.insert_one(doc)

    # Notify every student in that subject's department/semester.
    students = await students_collection.find(
        {"department": subject["department"], "semester": subject["semester"]}
    ).to_list(length=5000)
    await notify_many(
        [s["user_id"] for s in students],
        title="New Assignment Posted",
        message=f'"{payload.title}" for {subject["name"]} is due {payload.due_date}.',
        notif_type="assignment_reminder",
        link=f"/student/assignments/{doc['_id']}",
    )
    return {"message": "Assignment created successfully.", "id": doc["_id"]}


@router.get("/subject/{subject_id}")
async def list_assignments_for_subject(subject_id: str, user=Depends(require_role("faculty", "admin", "student"))):
    if user["role"] == "student":
        student = await students_collection.find_one({"user_id": user["_id"]})
        subject = await subjects_collection.find_one({"_id": subject_id})
        if not student or not subject or not is_enrolled(student, subject):
            raise HTTPException(403, "You are not enrolled in this subject.")
    else:
        await assert_can_manage_subject(user, subject_id)
    assignments = await assignments_collection.find({"subject_id": subject_id}).to_list(length=1000)
    return [{**a, "id": a["_id"]} for a in assignments]


@router.get("/mine")
async def my_assignments(user=Depends(require_role("student"))):
    """All assignments for the student's department + semester, with their own submission status."""
    student = await students_collection.find_one({"user_id": user["_id"]})
    if not student:
        raise HTTPException(404, "Student profile not found.")

    subjects = await subjects_collection.find(
        {"department": student["department"], "semester": student["semester"]}
    ).to_list(length=1000)
    subject_ids = [s["_id"] for s in subjects]
    subjects_by_id = {s["_id"]: s for s in subjects}

    assignments = await assignments_collection.find({"subject_id": {"$in": subject_ids}}).to_list(length=1000)
    assignment_ids = [a["_id"] for a in assignments]
    submissions = await submissions_collection.find(
        {"assignment_id": {"$in": assignment_ids}, "student_id": student["_id"]}
    ).to_list(length=1000)
    submissions_by_assignment = {s["assignment_id"]: s for s in submissions}

    today = datetime.now(timezone.utc).date().isoformat()
    result = []
    for a in assignments:
        sub = submissions_by_assignment.get(a["_id"])
        result.append({
            "id": a["_id"],
            "title": a["title"],
            "description": a["description"],
            "subject_name": subjects_by_id.get(a["subject_id"], {}).get("name"),
            "due_date": a["due_date"],
            "is_due_today": a["due_date"] == today,
            "is_overdue": a["due_date"] < today,
            "submission_status": sub["status"] if sub else "not_submitted",
            "grade": sub.get("grade") if sub else None,
        })
    return result


@router.post("/{assignment_id}/submit")
async def submit_assignment(assignment_id: str, payload: SubmitAssignmentRequest, user=Depends(require_role("student"))):
    assignment = await assignments_collection.find_one({"_id": assignment_id})
    if not assignment:
        raise HTTPException(404, "Assignment not found.")
    student = await students_collection.find_one({"user_id": user["_id"]})
    if not student:
        raise HTTPException(404, "Student profile not found.")
    subject = await subjects_collection.find_one({"_id": assignment["subject_id"]})
    if not subject or not is_enrolled(student, subject):
        raise HTTPException(403, "This assignment isn't for your class.")

    existing = await submissions_collection.find_one({"assignment_id": assignment_id, "student_id": student["_id"]})
    if existing:
        await submissions_collection.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {"file_url": payload.file_url, "status": "submitted", "submitted_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)},
                "$push": {"timeline": timeline_event("Final Submitted" if existing["status"] != "submitted" else "Updated")},
            },
        )
        return {"message": "Assignment updated successfully."}

    doc = new_submission_document(assignment_id, student["_id"], payload.file_url)
    await submissions_collection.insert_one(doc)
    await award_xp(user["_id"], "early_submission" if today_str() < assignment["due_date"] else "on_time_submission", note=assignment["title"])

    faculty = await faculty_collection.find_one({"faculty_id": assignment["faculty_id"]})
    if faculty:
        await notify_user(
            faculty["user_id"],
            title="New Submission",
            message=f'{user["full_name"]} submitted "{assignment["title"]}".',
            notif_type="new_submission",
            link=f"/faculty/assignments/{assignment_id}",
        )
    return {"message": "Assignment submitted successfully."}


@router.get("/{assignment_id}/submissions")
async def list_submissions(assignment_id: str, user=Depends(require_role("faculty", "admin"))):
    assignment = await assignments_collection.find_one({"_id": assignment_id})
    if not assignment:
        raise HTTPException(404, "Assignment not found.")
    await assert_can_manage_subject(user, assignment["subject_id"])
    submissions = await submissions_collection.find({"assignment_id": assignment_id}).to_list(length=5000)
    student_ids = [s["student_id"] for s in submissions]
    students = await students_collection.find({"_id": {"$in": student_ids}}).to_list(length=5000)
    students_by_id = {s["_id"]: s for s in students}
    user_ids = [s["user_id"] for s in students]
    users = await users_collection.find({"_id": {"$in": user_ids}}).to_list(length=5000)
    users_by_student_userid = {u["_id"]: u for u in users}

    result = []
    for s in submissions:
        student = students_by_id.get(s["student_id"], {})
        u = users_by_student_userid.get(student.get("user_id"), {})
        result.append({
            "id": s["_id"],
            "student_name": u.get("full_name"),
            "student_roll": student.get("student_id"),
            "file_url": s["file_url"],
            "status": s["status"],
            "grade": s.get("grade"),
            "feedback": s.get("feedback"),
            "submitted_at": s.get("submitted_at"),
            "timeline": s.get("timeline", []),   # Assignment DNA
        })
    return result


@router.put("/submissions/{submission_id}/grade")
async def grade_submission(submission_id: str, payload: GradeSubmissionRequest, user=Depends(require_role("faculty", "admin"))):
    submission = await submissions_collection.find_one({"_id": submission_id})
    if not submission:
        raise HTTPException(404, "Submission not found.")
    assignment = await assignments_collection.find_one({"_id": submission["assignment_id"]})
    if not assignment:
        raise HTTPException(404, "Assignment not found.")
    await assert_can_manage_subject(user, assignment["subject_id"])

    await submissions_collection.update_one(
        {"_id": submission_id},
        {
            "$set": {"grade": payload.grade, "feedback": payload.feedback, "status": "graded", "updated_at": datetime.now(timezone.utc)},
            "$push": {"timeline": timeline_event(f"Graded: {payload.grade}")},
        },
    )

    student = await students_collection.find_one({"_id": submission["student_id"]})
    if student:
        await notify_user(
            student["user_id"],
            title="Assignment Graded",
            message=f"You received grade {payload.grade}.",
            notif_type="assignment_reminder",
        )
    return {"message": "Submission graded successfully."}
