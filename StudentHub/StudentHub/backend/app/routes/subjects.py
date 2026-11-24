"""
routes/subjects.py
Admin creates subjects and maps them to a semester/department and to ONE OR MORE faculty members
(many-to-many via the `faculty_subjects` collection). Changing a subject's teachers never touches any other
subject, and removing a teacher never deletes marks/attendance/notes/assignments.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.database import subjects_collection, faculty_collection, users_collection, faculty_subjects_collection
from app.auth import require_role, get_current_user
from app.models.subject import new_subject_document
from app.schemas.academic import CreateSubjectRequest, UpdateSubjectRequest
from app.services import faculty_subject_links as links

router = APIRouter(prefix="/subjects", tags=["Subject Management"])


async def _faculty_by_id(ids: list[str]) -> dict:
    docs = await faculty_collection.find({"faculty_id": {"$in": list(ids)}}).to_list(length=2000)
    users = {u["_id"]: u for u in await users_collection.find({"_id": {"$in": [d["user_id"] for d in docs]}}).to_list(length=2000)}
    return {d["faculty_id"]: {"faculty_id": d["faculty_id"], "full_name": users.get(d["user_id"], {}).get("full_name")} for d in docs}


async def _require_real_faculty(faculty_ids: list[str]) -> None:
    found = await faculty_collection.find({"faculty_id": {"$in": faculty_ids}}).to_list(length=2000)
    if len({f["faculty_id"] for f in found}) != len(set(faculty_ids)):
        raise HTTPException(400, "No faculty member found with that Faculty ID.")


def _present(subject: dict, faculty_ids: list[str], faculty_info: dict) -> dict:
    out = {k: v for k, v in subject.items() if k != "faculty_id"}   # legacy single-teacher field is never exposed
    out["id"] = subject["_id"]
    out["faculty_ids"] = faculty_ids
    out["faculty"] = [faculty_info[f] for f in faculty_ids if f in faculty_info]
    return out


@router.get("")
async def list_subjects(department: Optional[str] = None, semester: Optional[int] = None, user=Depends(get_current_user)):
    query: dict = {}
    if department:
        query["department"] = department
    if semester:
        query["semester"] = semester
    subjects = await subjects_collection.find(query).sort("name", 1).to_list(length=1000)
    all_links = await faculty_subjects_collection.find({"subject_id": {"$in": [s["_id"] for s in subjects]}}).to_list(length=100000)
    by_subject: dict = {}
    for l in all_links:
        by_subject.setdefault(l["subject_id"], []).append(l["faculty_id"])
    info = await _faculty_by_id(list({f for fs in by_subject.values() for f in fs}))
    return [_present(s, by_subject.get(s["_id"], []), info) for s in subjects]


@router.get("/{subject_id}/faculty")
async def faculty_for_subject(subject_id: str, admin=Depends(require_role("admin"))):
    if not await subjects_collection.find_one({"_id": subject_id}):
        raise HTTPException(404, "Subject not found.")
    ids = await links.faculty_ids_for_subject(subject_id)
    info = await _faculty_by_id(ids)
    return [info[i] for i in ids if i in info]


@router.post("", status_code=201)
async def create_subject(payload: CreateSubjectRequest, admin=Depends(require_role("admin"))):
    if await subjects_collection.find_one({"code": payload.code}):
        raise HTTPException(409, "A subject with this code already exists.")
    wanted = list(dict.fromkeys(([payload.faculty_id] if payload.faculty_id else []) + list(payload.faculty_ids)))
    if wanted:
        await _require_real_faculty(wanted)

    doc = new_subject_document(name=payload.name, code=payload.code, department=payload.department,
                               semester=payload.semester, credits=payload.credits)
    await subjects_collection.insert_one(doc)
    if wanted:
        await links.add_links_for_subject(doc["_id"], wanted, assigned_by=admin["_id"])
    return {"message": "Subject created successfully.", "id": doc["_id"]}


@router.put("/{subject_id}")
async def update_subject(subject_id: str, payload: UpdateSubjectRequest, admin=Depends(require_role("admin"))):
    subject = await subjects_collection.find_one({"_id": subject_id})
    if not subject:
        raise HTTPException(404, "Subject not found.")

    sent = payload.model_fields_set
    if "faculty_ids" in sent and payload.faculty_ids is not None:
        await _require_real_faculty(payload.faculty_ids)
    if "faculty_id" in sent and payload.faculty_id:
        await _require_real_faculty([payload.faculty_id])

    fields = {k: getattr(payload, k) for k in ("name", "semester", "credits") if k in sent and getattr(payload, k) is not None}
    if fields:
        await subjects_collection.update_one({"_id": subject_id}, {"$set": fields})

    if "faculty_ids" in sent and payload.faculty_ids is not None:
        await links.replace_for_subject(subject_id, payload.faculty_ids, assigned_by=admin["_id"])
    elif "faculty_id" in sent and payload.faculty_id:
        await links.add_links_for_subject(subject_id, [payload.faculty_id], assigned_by=admin["_id"])
    return {"message": "Subject updated successfully."}


@router.delete("/{subject_id}")
async def delete_subject(subject_id: str, admin=Depends(require_role("admin"))):
    result = await subjects_collection.delete_one({"_id": subject_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Subject not found.")
    await links.remove_all_for_subject(subject_id)
    return {"message": "Subject deleted successfully."}
