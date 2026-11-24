"""
routes/locker.py
Digital Study Locker: a single searchable view over everything a student has
already collected — faculty-uploaded notes for their own department/semester,
their own AI Study Coach materials, and their generated flashcard decks —
without duplicating any of that data into a new collection.
"""
from fastapi import APIRouter, Depends

from app.database import uploaded_notes_collection, students_collection, subjects_collection, study_plans_collection, flashcards_collection
from app.auth import require_role

router = APIRouter(prefix="/locker", tags=["Digital Study Locker"])


@router.get("")
async def my_locker(q: str | None = None, user=Depends(require_role("student"))):
    needle = (q or "").strip().lower()
    items = []

    student = await students_collection.find_one({"user_id": user["_id"]})
    if student:
        subjects = await subjects_collection.find({"department": student["department"], "semester": student["semester"]}).to_list(length=200)
        subject_ids = [s["_id"] for s in subjects]
        subj_by_id = {s["_id"]: s for s in subjects}
        notes = await uploaded_notes_collection.find({"subject_id": {"$in": subject_ids}}).to_list(length=2000)
        for n in notes:
            if needle and needle not in n["title"].lower():
                continue
            items.append({
                "kind": "note", "id": n["_id"], "title": n["title"],
                "subtitle": f"{subj_by_id.get(n['subject_id'], {}).get('name', 'Subject')} · {n['file_type'].upper()}",
                "file_url": n["file_url"], "created_at": n["created_at"],
            })

    plans = await study_plans_collection.find({"user_id": user["_id"]}).to_list(length=500)
    for p in plans:
        if needle and needle not in p["subject"].lower():
            continue
        items.append({"kind": "ai_notes", "id": p["_id"], "title": f"AI Notes — {p['subject']}", "subtitle": f"Exam {p['exam_date']}", "file_url": None, "created_at": p["created_at"]})

        cards = await flashcards_collection.count_documents({"plan_id": p["_id"]})
        if cards and (not needle or needle in p["subject"].lower()):
            items.append({"kind": "flashcards", "id": p["_id"], "title": f"Flashcards — {p['subject']}", "subtitle": f"{cards} cards", "file_url": None, "created_at": p["created_at"]})

    items.sort(key=lambda x: x["created_at"], reverse=True)
    return {"query": q, "count": len(items), "items": items}
