"""models/study_material.py — `study_materials` collection: one document per file the student uploads to the AI Study Coach."""
import uuid
from datetime import datetime, timezone


def new_material_document(user_id: str, filename: str, file_url: str, kind: str, extracted_text: str, subject: str, confidence: float) -> dict:
    return {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "filename": filename,
        "file_url": file_url,
        "kind": kind,                 # "text" | "image"
        "extracted_text": extracted_text,
        "subject": subject,
        "subject_confidence": confidence,
        "created_at": datetime.now(timezone.utc),
    }
