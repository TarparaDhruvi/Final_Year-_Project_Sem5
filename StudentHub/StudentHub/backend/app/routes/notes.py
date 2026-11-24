"""
routes/notes.py
Faculty upload notes (PDF/PPT/DOCX/Images) organized by subject + unit +
semester; students download and filter. Files are saved to backend/uploads
and served back via a static file_url the frontend can open directly.
"""

import os
import uuid
from app.services.faculty_subject_links import is_assigned
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional

from app.database import uploaded_notes_collection, subjects_collection, students_collection, faculty_collection
from app.auth import require_role
from app.models.note import new_note_document
from app.services.notifications import notify_many

router = APIRouter(prefix="/notes", tags=["Notes"])

ALLOWED_EXTENSIONS = {".pdf": "pdf", ".ppt": "ppt", ".pptx": "ppt", ".doc": "docx", ".docx": "docx",
                       ".jpg": "image", ".jpeg": "image", ".png": "image"}
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "notes")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", status_code=201)
async def upload_note(
    title: str = Form(...),
    subject_id: str = Form(...),
    unit: str = Form(...),
    file: UploadFile = File(...),
    user=Depends(require_role("faculty")),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Unsupported file type. Allowed: PDF, PPT, DOCX, JPG, PNG.")

    subject = await subjects_collection.find_one({"_id": subject_id})
    if not subject:
        raise HTTPException(404, "Subject not found.")

    faculty = await faculty_collection.find_one({"user_id": user["_id"]})
    if not faculty or not await is_assigned(faculty["faculty_id"], subject_id):
        raise HTTPException(403, "You are not assigned to this subject.")

    stored_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    file_url = f"/uploads/notes/{stored_name}"
    doc = new_note_document(title, subject_id, unit, subject["semester"], file_url, ALLOWED_EXTENSIONS[ext], user["_id"])
    await uploaded_notes_collection.insert_one(doc)

    students = await students_collection.find({"department": subject["department"], "semester": subject["semester"]}).to_list(length=5000)
    await notify_many([s["user_id"] for s in students], "New Notes Uploaded", f'"{title}" was added to {subject["name"]}.', "new_note")

    return {"message": "Notes uploaded successfully.", "id": doc["_id"], "file_url": file_url}


@router.get("")
async def list_notes(subject_id: Optional[str] = None, unit: Optional[str] = None, user=Depends(require_role("student", "faculty", "admin"))):
    query: dict = {}
    if subject_id:
        query["subject_id"] = subject_id
    if unit:
        query["unit"] = unit
    notes = await uploaded_notes_collection.find(query).sort("created_at", -1).to_list(length=1000)
    return [{**n, "id": n["_id"]} for n in notes]


@router.post("/{note_id}/view")
async def record_view(note_id: str, user=Depends(require_role("student", "faculty", "admin"))):
    """Called by the frontend right before opening a note — powers the Faculty Heatmap's 'most viewed notes'."""
    result = await uploaded_notes_collection.update_one({"_id": note_id}, {"$inc": {"views": 1}})
    if result.matched_count == 0:
        raise HTTPException(404, "Note not found.")
    return {"message": "View recorded."}


@router.delete("/{note_id}")
async def delete_note(note_id: str, user=Depends(require_role("faculty", "admin"))):
    result = await uploaded_notes_collection.delete_one({"_id": note_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Note not found.")
    return {"message": "Note deleted successfully."}
