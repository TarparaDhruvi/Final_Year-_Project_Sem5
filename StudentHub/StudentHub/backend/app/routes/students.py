"""
routes/students.py
Admin student management: list / search / filter, full profile with academic records, add, edit,
activate / deactivate, delete, and reset a student's password. Creating a student creates BOTH a
`users` row (login) and a `students` row (academic profile). Duplicates (email, Student ID) are
rejected up front AND by the unique indexes (a race between two admins returns a clean 409, not a 500),
and a half-created student is rolled back so no orphan login can be left behind.

GET /students/roster is the one endpoint here that Faculty may call, restricted to their own subjects.
"""
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from app.database import (
    users_collection, students_collection, subjects_collection, leave_requests_collection, refresh_tokens_collection,
)
from app.auth import require_role, hash_password
from app.models.user import new_user_document
from app.models.student import new_student_document
from app.schemas.academic import CreateStudentRequest, UpdateStudentRequest, StudentStatusRequest
from app.services.access import assert_can_manage_subject
from app.services.student_records import academic_record

router = APIRouter(prefix="/students", tags=["Student Management (Admin)"])


def _row(s: dict, u: dict) -> dict:
    return {
        "id": s["_id"], "user_id": s["user_id"], "student_id": s["student_id"],
        "full_name": u.get("full_name"), "email": u.get("email"), "phone": u.get("phone"),
        "department": s["department"], "semester": s["semester"], "batch": s.get("batch"),
        "is_verified": u.get("is_verified", False), "is_active": u.get("is_active", True),
        "created_at": s.get("created_at"),
    }


@router.get("")
async def list_students(
    search: Optional[str] = None,
    department: Optional[str] = None,
    semester: Optional[int] = None,
    status: Optional[str] = None,          # active | inactive | unverified
    admin=Depends(require_role("admin")),
):
    query: dict = {}
    if department:
        query["department"] = department
    if semester:
        query["semester"] = semester
    if status and status not in ("active", "inactive", "unverified"):
        raise HTTPException(400, "status must be 'active', 'inactive' or 'unverified'.")

    students = await students_collection.find(query).sort("student_id", 1).to_list(length=5000)
    users = await users_collection.find({"_id": {"$in": [s["user_id"] for s in students]}}).to_list(length=5000)
    users_by_id = {u["_id"]: u for u in users}

    needle = (search or "").strip().lower()
    results = []
    for s in students:
        u = users_by_id.get(s["user_id"], {})
        if needle and not any(needle in str(v or "").lower() for v in (u.get("full_name"), s["student_id"], u.get("email"), u.get("phone"))):
            continue
        if status == "active" and not u.get("is_active", True):
            continue
        if status == "inactive" and u.get("is_active", True):
            continue
        if status == "unverified" and u.get("is_verified", False):
            continue
        results.append(_row(s, u))
    return results


@router.get("/roster")
async def subject_roster(subject_id: str, user=Depends(require_role("admin", "faculty"))):
    """Students enrolled in a subject (same department + semester). Faculty may only request the roster
    of a subject the Admin assigned to them."""
    subject = await assert_can_manage_subject(user, subject_id)
    students = await students_collection.find(
        {"department": subject["department"], "semester": subject["semester"]}
    ).sort("student_id", 1).to_list(length=5000)
    users = await users_collection.find({"_id": {"$in": [s["user_id"] for s in students]}}).to_list(length=5000)
    users_by_id = {u["_id"]: u for u in users}
    return [
        {
            "id": s["_id"], "user_id": s["user_id"], "student_id": s["student_id"],
            "full_name": users_by_id.get(s["user_id"], {}).get("full_name"),
            "email": users_by_id.get(s["user_id"], {}).get("email"),
            "department": s["department"], "semester": s["semester"],
        }
        for s in students
    ]


@router.get("/{student_doc_id}")
async def student_profile(student_doc_id: str, admin=Depends(require_role("admin"))):
    """Full profile: account details + attendance / marks / assignments per subject + recent leave."""
    student = await students_collection.find_one({"_id": student_doc_id})
    if not student:
        raise HTTPException(404, "Student not found.")
    user = await users_collection.find_one({"_id": student["user_id"]}) or {}
    subjects = await subjects_collection.find(
        {"department": student["department"], "semester": student["semester"]}).sort("name", 1).to_list(length=500)
    leaves = await leave_requests_collection.find({"user_id": student["user_id"]}).sort("created_at", -1).to_list(length=20)
    return {
        **_row(student, user),
        "last_login_at": user.get("last_login_at"),
        "academics": await academic_record(student, subjects),
        "leave": [{"id": l["_id"], "from_date": l.get("from_date"), "to_date": l.get("to_date"), "reason": l.get("reason"), "status": l.get("status")} for l in leaves],
    }


@router.post("", status_code=201)
async def create_student(payload: CreateStudentRequest, admin=Depends(require_role("admin"))):
    if await users_collection.find_one({"email": payload.email}):
        raise HTTPException(409, "An account with this email already exists.")
    if await students_collection.find_one({"student_id": payload.student_id}) or await users_collection.find_one({"login_id": payload.student_id}):
        raise HTTPException(409, "A student with this Student ID already exists.")

    user_doc = new_user_document(
        full_name=payload.full_name, email=payload.email, hashed_password=hash_password(payload.password),
        role="student", phone=payload.phone,
        is_verified=True,   # Admin-created accounts are pre-verified.
        login_id=payload.student_id,
    )
    student_doc = new_student_document(
        user_id=user_doc["_id"], student_id=payload.student_id, department=payload.department,
        semester=payload.semester, batch=payload.batch,
    )
    try:
        await users_collection.insert_one(user_doc)
        await students_collection.insert_one(student_doc)
    except DuplicateKeyError:
        await users_collection.delete_one({"_id": user_doc["_id"]})   # never leave an orphan login behind
        raise HTTPException(409, "A student with this email or Student ID already exists.")
    except Exception:
        await users_collection.delete_one({"_id": user_doc["_id"]})
        raise
    return {"message": "Student created successfully.", "id": student_doc["_id"]}


@router.put("/{student_doc_id}")
async def update_student(student_doc_id: str, payload: UpdateStudentRequest, admin=Depends(require_role("admin"))):
    student = await students_collection.find_one({"_id": student_doc_id})
    if not student:
        raise HTTPException(404, "Student not found.")
    user = await users_collection.find_one({"_id": student["user_id"]})
    if not user:
        raise HTTPException(404, "Linked user account not found.")

    sent = payload.model_fields_set
    new_email = payload.email if "email" in sent else None
    new_sid = payload.student_id if "student_id" in sent else None

    if new_email and new_email != user.get("email"):
        if await users_collection.find_one({"email": new_email, "_id": {"$ne": user["_id"]}}):
            raise HTTPException(409, "Another account already uses this email.")
    if new_sid and new_sid != student["student_id"]:
        if (await students_collection.find_one({"student_id": new_sid, "_id": {"$ne": student["_id"]}})
                or await users_collection.find_one({"login_id": new_sid, "_id": {"$ne": user["_id"]}})):
            raise HTTPException(409, "Another student already has this Student ID.")

    now = datetime.now(timezone.utc)
    student_fields: dict = {}
    for key in ("department", "semester"):
        if key in sent and getattr(payload, key) is not None:
            student_fields[key] = getattr(payload, key)
    if "batch" in sent:
        student_fields["batch"] = payload.batch or None
    if new_sid:
        student_fields["student_id"] = new_sid

    user_fields: dict = {}
    for key in ("full_name", "phone"):
        if key in sent and getattr(payload, key) is not None:
            user_fields[key] = getattr(payload, key)
    if new_email:
        user_fields["email"] = new_email
    if new_sid:
        user_fields["login_id"] = new_sid

    if not student_fields and not user_fields:
        return {"message": "Nothing to update."}
    try:
        if user_fields:
            await users_collection.update_one({"_id": user["_id"]}, {"$set": {**user_fields, "updated_at": now}})
        if student_fields:
            await students_collection.update_one({"_id": student["_id"]}, {"$set": {**student_fields, "updated_at": now}})
    except DuplicateKeyError:
        raise HTTPException(409, "That email or Student ID is already in use.")
    return {"message": "Student updated successfully."}


@router.patch("/{student_doc_id}/status")
async def set_student_status(student_doc_id: str, payload: StudentStatusRequest, admin=Depends(require_role("admin"))):
    """Deactivate (blocks login and revokes sessions, keeps every record) or reactivate a student."""
    student = await students_collection.find_one({"_id": student_doc_id})
    if not student:
        raise HTTPException(404, "Student not found.")
    await users_collection.update_one(
        {"_id": student["user_id"]}, {"$set": {"is_active": payload.is_active, "updated_at": datetime.now(timezone.utc)}})
    if not payload.is_active:
        await refresh_tokens_collection.update_many({"user_id": student["user_id"]}, {"$set": {"revoked": True}})
    return {"message": "Student activated." if payload.is_active else "Student deactivated. They can no longer log in.", "is_active": payload.is_active}


@router.delete("/{student_doc_id}")
async def delete_student(student_doc_id: str, admin=Depends(require_role("admin"))):
    student = await students_collection.find_one({"_id": student_doc_id})
    if not student:
        raise HTTPException(404, "Student not found.")
    await students_collection.delete_one({"_id": student_doc_id})
    await users_collection.delete_one({"_id": student["user_id"]})
    await refresh_tokens_collection.update_many({"user_id": student["user_id"]}, {"$set": {"revoked": True}})
    return {"message": "Student deleted successfully."}


@router.post("/{student_doc_id}/reset-password")
async def reset_student_password(student_doc_id: str, admin=Depends(require_role("admin"))):
    student = await students_collection.find_one({"_id": student_doc_id})
    if not student:
        raise HTTPException(404, "Student not found.")
    user = await users_collection.find_one({"_id": student["user_id"]})
    if not user:
        raise HTTPException(404, "Linked user account not found.")

    # token_urlsafe(9) can lack an uppercase/digit/special char, so build one that satisfies the app's password rules.
    temp_password = f"{secrets.token_urlsafe(9)}Aa1@"
    await users_collection.update_one({"_id": user["_id"]}, {"$set": {"hashed_password": hash_password(temp_password)}})
    await refresh_tokens_collection.update_many({"user_id": user["_id"]}, {"$set": {"revoked": True}})
    # In production this would email the temp password; for now it's returned to the admin to hand
    # off securely, since SMTP may not be configured for every deployment.
    return {"message": "Password reset. Share this temporary password with the student.", "temporary_password": temp_password}
