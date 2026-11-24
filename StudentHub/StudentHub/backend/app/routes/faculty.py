"""
routes/faculty.py
Admin-only faculty management (add, edit, delete, assign subjects) plus
faculty-facing `GET /faculty/me/subjects`, which powers the subject dropdown on
every faculty screen (Attendance, Assignments, Notes/Study Material, Marks...).
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.database import users_collection, faculty_collection, subjects_collection
from app.auth import require_role, hash_password, get_current_user
from app.models.user import new_user_document
from app.models.faculty import new_faculty_document
from app.schemas.academic import CreateFacultyRequest, UpdateFacultyRequest, AssignSubjectsRequest, AddSubjectsRequest, ReassignSubjectRequest
from app.database import faculty_subjects_collection
from app.services import faculty_subject_links as links

router = APIRouter(prefix="/faculty", tags=["Faculty"])


@router.get("/directory")
async def faculty_directory(user=Depends(get_current_user)):
    """Student/Faculty-safe faculty list (name + ID + department only)."""
    faculty_list = await faculty_collection.find({}).sort("faculty_id", 1).to_list(length=1000)
    users = await users_collection.find({"_id": {"$in": [f["user_id"] for f in faculty_list]}}).to_list(length=1000)
    users_by_id = {u["_id"]: u for u in users}
    return [
        {"faculty_id": f["faculty_id"], "full_name": users_by_id.get(f["user_id"], {}).get("full_name", "—"), "department": f["department"]}
        for f in faculty_list
    ]


@router.get("/me/subjects")
async def my_subjects(user=Depends(require_role("faculty"))):
    """Every subject the Admin has assigned to the logged-in faculty member (always fresh from MongoDB)."""
    faculty = await faculty_collection.find_one({"user_id": user["_id"]})
    if not faculty:
        return []
    subjects = await links.subjects_for_faculty(faculty["faculty_id"])
    return [{**{k: v for k, v in s.items() if k != "faculty_id"}, "id": s["_id"]} for s in subjects]


@router.get("")
async def list_faculty(department: Optional[str] = None, admin=Depends(require_role("admin"))):
    query = {"department": department} if department else {}
    faculty_list = await faculty_collection.find(query).to_list(length=1000)
    users = await users_collection.find({"_id": {"$in": [f["user_id"] for f in faculty_list]}}).to_list(length=1000)
    users_by_id = {u["_id"]: u for u in users}

    # Derive assignments from the link collection so the Admin view can never drift from reality.
    all_links = await faculty_subjects_collection.find({}).to_list(length=100000)
    subject_ids_by_faculty: dict = {}
    for l in all_links:
        subject_ids_by_faculty.setdefault(l["faculty_id"], []).append(l["subject_id"])

    return [
        {
            "id": f["_id"],
            "user_id": f["user_id"],
            "faculty_id": f["faculty_id"],
            "full_name": users_by_id.get(f["user_id"], {}).get("full_name"),
            "email": users_by_id.get(f["user_id"], {}).get("email"),
            "phone": users_by_id.get(f["user_id"], {}).get("phone"),
            "department": f["department"],
            "designation": f.get("designation"),
            "subject_ids": subject_ids_by_faculty.get(f["faculty_id"], []),
        }
        for f in faculty_list
    ]


@router.post("", status_code=201)
async def create_faculty(payload: CreateFacultyRequest, admin=Depends(require_role("admin"))):
    if await users_collection.find_one({"email": payload.email}):
        raise HTTPException(409, "An account with this email already exists.")
    if await faculty_collection.find_one({"faculty_id": payload.faculty_id}) or await users_collection.find_one({"login_id": payload.faculty_id}):
        raise HTTPException(409, "A faculty member with this Faculty ID already exists.")

    user_doc = new_user_document(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role="faculty",
        phone=payload.phone,
        is_verified=True,
        login_id=payload.faculty_id,
    )
    await users_collection.insert_one(user_doc)

    faculty_doc = new_faculty_document(
        user_id=user_doc["_id"],
        faculty_id=payload.faculty_id,
        department=payload.department,
        designation=payload.designation,
    )
    await faculty_collection.insert_one(faculty_doc)
    return {"message": "Faculty member created successfully.", "id": faculty_doc["_id"]}


@router.put("/{faculty_doc_id}")
async def update_faculty(faculty_doc_id: str, payload: UpdateFacultyRequest, admin=Depends(require_role("admin"))):
    faculty = await faculty_collection.find_one({"_id": faculty_doc_id})
    if not faculty:
        raise HTTPException(404, "Faculty member not found.")

    data = payload.model_dump()
    academic_fields = {k: v for k, v in data.items() if v is not None and k in ("department", "designation")}
    if academic_fields:
        await faculty_collection.update_one({"_id": faculty_doc_id}, {"$set": academic_fields})
    user_fields = {k: v for k, v in data.items() if v is not None and k in ("full_name", "phone")}
    if user_fields:
        await users_collection.update_one({"_id": faculty["user_id"]}, {"$set": user_fields})
    return {"message": "Faculty member updated successfully."}


@router.delete("/{faculty_doc_id}")
async def delete_faculty(faculty_doc_id: str, admin=Depends(require_role("admin"))):
    faculty = await faculty_collection.find_one({"_id": faculty_doc_id})
    if not faculty:
        raise HTTPException(404, "Faculty member not found.")
    # Remove only THIS faculty member's links; the subjects (and any co-teachers) stay untouched.
    await links.remove_all_for_faculty(faculty["faculty_id"])
    await faculty_collection.delete_one({"_id": faculty_doc_id})
    await users_collection.delete_one({"_id": faculty["user_id"]})
    return {"message": "Faculty member deleted successfully."}


async def _faculty_or_404(faculty_doc_id: str) -> dict:
    faculty = await faculty_collection.find_one({"_id": faculty_doc_id})
    if not faculty:
        raise HTTPException(404, "Faculty member not found.")
    return faculty


async def _require_subjects(subject_ids: list[str]) -> None:
    found = await subjects_collection.find({"_id": {"$in": subject_ids}}).to_list(length=5000)
    if len(found) != len(set(subject_ids)):
        raise HTTPException(400, "One or more subject IDs are invalid.")


@router.get("/assignments")
async def assignment_overview(admin=Depends(require_role("admin"))):
    """Both directions in one call: every faculty member's subjects AND every subject's faculty."""
    faculty_list = await faculty_collection.find({}).sort("faculty_id", 1).to_list(length=2000)
    users = {u["_id"]: u for u in await users_collection.find({"_id": {"$in": [f["user_id"] for f in faculty_list]}}).to_list(length=2000)}
    subjects = await subjects_collection.find({}).sort("name", 1).to_list(length=5000)
    all_links = await faculty_subjects_collection.find({}).to_list(length=100000)
    subs_of: dict = {}
    facs_of: dict = {}
    for l in all_links:
        subs_of.setdefault(l["faculty_id"], []).append(l["subject_id"])
        facs_of.setdefault(l["subject_id"], []).append(l["faculty_id"])
    names = {f["faculty_id"]: users.get(f["user_id"], {}).get("full_name") for f in faculty_list}
    subj_by_id = {s["_id"]: s for s in subjects}
    return {
        "by_faculty": [
            {"faculty_id": f["faculty_id"], "full_name": names[f["faculty_id"]],
             "subjects": [{"id": sid, "name": subj_by_id[sid]["name"], "code": subj_by_id[sid]["code"]} for sid in subs_of.get(f["faculty_id"], []) if sid in subj_by_id]}
            for f in faculty_list
        ],
        "by_subject": [
            {"id": s["_id"], "name": s["name"], "code": s["code"], "department": s["department"], "semester": s["semester"],
             "faculty": [{"faculty_id": fid, "full_name": names.get(fid)} for fid in facs_of.get(s["_id"], [])]}
            for s in subjects
        ],
    }


@router.put("/{faculty_doc_id}/assign-subjects")
async def assign_subjects(faculty_doc_id: str, payload: AssignSubjectsRequest, admin=Depends(require_role("admin"))):
    """Sets THIS faculty member's subject list to exactly `subject_ids`. Subjects keep every other teacher they have."""
    faculty = await _faculty_or_404(faculty_doc_id)
    wanted = list(dict.fromkeys(payload.subject_ids))
    await _require_subjects(wanted)
    added, removed = await links.replace_for_faculty(faculty["faculty_id"], wanted, assigned_by=admin["_id"])
    return {"message": "Subjects assigned successfully.", "subject_ids": wanted, "added": added, "removed": removed}


@router.post("/{faculty_doc_id}/subjects")
async def add_subjects(faculty_doc_id: str, payload: AddSubjectsRequest, admin=Depends(require_role("admin"))):
    """Adds subjects to this faculty member WITHOUT affecting their existing subjects or any other faculty."""
    faculty = await _faculty_or_404(faculty_doc_id)
    wanted = list(dict.fromkeys(payload.subject_ids))
    await _require_subjects(wanted)
    added, existing = await links.add_links(faculty["faculty_id"], wanted, assigned_by=admin["_id"])
    if not added:
        raise HTTPException(409, "These subjects are already assigned to this faculty member.")
    return {"message": f"{len(added)} subject(s) assigned.", "added": added, "already_assigned": existing}


@router.post("/{faculty_doc_id}/subjects/remove")
async def remove_subjects(faculty_doc_id: str, payload: AddSubjectsRequest, admin=Depends(require_role("admin"))):
    """Removes the selected subjects from THIS faculty member only. Co-teachers and all academic records are kept."""
    faculty = await _faculty_or_404(faculty_doc_id)
    current = set(await links.subject_ids_for_faculty(faculty["faculty_id"]))
    selected = [s for s in dict.fromkeys(payload.subject_ids) if s in current]
    if not selected:
        raise HTTPException(404, "None of those subjects are assigned to this faculty member.")
    removed = await links.remove_links(faculty["faculty_id"], selected)
    return {"message": f"{removed} assignment(s) removed.", "removed": selected}


@router.delete("/{faculty_doc_id}/subjects/{subject_id}")
async def remove_one_subject(faculty_doc_id: str, subject_id: str, admin=Depends(require_role("admin"))):
    faculty = await _faculty_or_404(faculty_doc_id)
    if not await links.is_assigned(faculty["faculty_id"], subject_id):
        raise HTTPException(404, "That subject is not assigned to this faculty member.")
    await links.remove_links(faculty["faculty_id"], [subject_id])
    return {"message": "Assignment removed. Other faculty teaching this subject are unaffected."}


@router.post("/{faculty_doc_id}/subjects/{subject_id}/reassign")
async def reassign_subject(faculty_doc_id: str, subject_id: str, payload: ReassignSubjectRequest, admin=Depends(require_role("admin"))):
    """Moves ONE subject from this faculty member to another. The new teacher is added first, so the subject can
    never end up with nobody if something fails half-way."""
    source = await _faculty_or_404(faculty_doc_id)
    target = await faculty_collection.find_one({"faculty_id": payload.to_faculty_id})
    if not target:
        raise HTTPException(404, "The faculty member to reassign to was not found.")
    if target["faculty_id"] == source["faculty_id"]:
        raise HTTPException(400, "Choose a different faculty member.")
    if not await links.is_assigned(source["faculty_id"], subject_id):
        raise HTTPException(404, "That subject is not assigned to this faculty member.")
    await links.add_links(target["faculty_id"], [subject_id], assigned_by=admin["_id"])
    await links.remove_links(source["faculty_id"], [subject_id])
    return {"message": "Subject reassigned."}
