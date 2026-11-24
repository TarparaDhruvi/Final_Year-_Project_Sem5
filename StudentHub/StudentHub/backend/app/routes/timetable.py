"""
routes/timetable.py
Admin creates/edits weekly timetable slots. Before saving, we check for
three kinds of clashes on the same day + overlapping time range:
faculty clash (same faculty double-booked), classroom clash (same room
double-booked), and batch clash (same department+semester double-booked).
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.database import timetable_collection, users_collection, subjects_collection
from app.auth import require_role, get_current_user
from app.models.timetable import new_timetable_document
from app.schemas.operations import CreateTimetableSlotRequest
from app.services.notifications import notify_many
from app.database import students_collection, faculty_collection
from app.services.faculty_subject_links import is_assigned, subject_ids_for_faculty

router = APIRouter(prefix="/timetable", tags=["Timetable"])


def _times_overlap(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    return start_a < end_b and start_b < end_a


async def _find_clashes(day_of_week: str, start_time: str, end_time: str, faculty_id: str,
                         classroom: str, department: str, semester: int, exclude_id: Optional[str] = None):
    query = {"day_of_week": day_of_week}
    if exclude_id:
        query["_id"] = {"$ne": exclude_id}

    same_day_slots = await timetable_collection.find(query).to_list(length=1000)
    clashes = []
    for slot in same_day_slots:
        if not _times_overlap(start_time, end_time, slot["start_time"], slot["end_time"]):
            continue
        if slot["faculty_id"] == faculty_id:
            clashes.append({"type": "faculty", "message": f"Faculty is already booked {slot['start_time']}-{slot['end_time']} on {day_of_week}."})
        if slot["classroom"] == classroom:
            clashes.append({"type": "classroom", "message": f"Classroom {classroom} is already booked {slot['start_time']}-{slot['end_time']} on {day_of_week}."})
        if slot["department"] == department and slot["semester"] == semester:
            clashes.append({"type": "batch", "message": f"This batch already has a class {slot['start_time']}-{slot['end_time']} on {day_of_week}."})
    return clashes


async def _require_teaches(faculty_id: str, subject_id: str) -> None:
    """A slot's teacher must be one of the faculty currently assigned to that subject (a subject may have several)."""
    if not await subjects_collection.find_one({"_id": subject_id}):
        raise HTTPException(404, "Subject not found.")
    if not await is_assigned(faculty_id, subject_id):
        raise HTTPException(400, "This faculty member is not assigned to the selected subject. Assign the subject first.")


@router.get("")
async def get_timetable(department: Optional[str] = None, semester: Optional[int] = None, user=Depends(get_current_user)):
    query: dict = {}
    if department:
        query["department"] = department
    if semester:
        query["semester"] = semester
    slots = await timetable_collection.find(query).to_list(length=2000)
    return [{**s, "id": s["_id"]} for s in slots]


@router.post("/check-clash")
async def check_clash(payload: CreateTimetableSlotRequest, admin=Depends(require_role("admin"))):
    """Lets the frontend show a live conflict warning before the admin hits Save."""
    clashes = await _find_clashes(
        payload.day_of_week, payload.start_time, payload.end_time,
        payload.faculty_id, payload.classroom, payload.department, payload.semester,
    )
    return {"has_clash": len(clashes) > 0, "clashes": clashes}


@router.post("", status_code=201)
async def create_timetable_slot(payload: CreateTimetableSlotRequest, admin=Depends(require_role("admin"))):
    await _require_teaches(payload.faculty_id, payload.subject_id)
    clashes = await _find_clashes(
        payload.day_of_week, payload.start_time, payload.end_time,
        payload.faculty_id, payload.classroom, payload.department, payload.semester,
    )
    if clashes:
        raise HTTPException(409, detail={"message": "Timetable conflict detected.", "clashes": clashes})

    doc = new_timetable_document(
        payload.day_of_week, payload.start_time, payload.end_time, payload.subject_id,
        payload.faculty_id, payload.classroom, payload.department, payload.semester,
    )
    await timetable_collection.insert_one(doc)

    faculty = await faculty_collection.find_one({"faculty_id": payload.faculty_id})
    students = await students_collection.find({"department": payload.department, "semester": payload.semester}).to_list(length=5000)
    recipient_ids = [s["user_id"] for s in students] + ([faculty["user_id"]] if faculty else [])
    await notify_many(recipient_ids, "Timetable Updated", f"A new class slot was added on {payload.day_of_week}.", "timetable_update")

    return {"message": "Timetable slot created successfully.", "id": doc["_id"]}


@router.put("/{slot_id}")
async def update_timetable_slot(slot_id: str, payload: CreateTimetableSlotRequest, admin=Depends(require_role("admin"))):
    existing = await timetable_collection.find_one({"_id": slot_id})
    if not existing:
        raise HTTPException(404, "Timetable slot not found.")
    await _require_teaches(payload.faculty_id, payload.subject_id)

    clashes = await _find_clashes(
        payload.day_of_week, payload.start_time, payload.end_time,
        payload.faculty_id, payload.classroom, payload.department, payload.semester,
        exclude_id=slot_id,
    )
    if clashes:
        raise HTTPException(409, detail={"message": "Timetable conflict detected.", "clashes": clashes})

    await timetable_collection.update_one({"_id": slot_id}, {"$set": payload.model_dump()})
    return {"message": "Timetable slot updated successfully."}


@router.delete("/{slot_id}")
async def delete_timetable_slot(slot_id: str, admin=Depends(require_role("admin"))):
    result = await timetable_collection.delete_one({"_id": slot_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Timetable slot not found.")
    return {"message": "Timetable slot deleted successfully."}


async def schedule_slots_for_user(user: dict) -> list[dict]:
    """Weekly timetable slots visible to this user, enriched with subject and faculty names.
    A faculty member gets only slots for subjects they CURRENTLY teach; a student gets their department + semester.
    Shared by /timetable/my-schedule, the Smart Calendar and the Faculty Classroom Activity Hub, so all three always agree."""
    if user["role"] == "faculty":
        faculty = await faculty_collection.find_one({"user_id": user["_id"]})
        # Only classes for subjects this faculty member CURRENTLY teaches (an unassigned subject drops off their schedule).
        mine = await subject_ids_for_faculty(faculty["faculty_id"]) if faculty else []
        query = {"faculty_id": faculty["faculty_id"], "subject_id": {"$in": mine}} if faculty else {"_id": None}
    else:
        student = await students_collection.find_one({"user_id": user["_id"]})
        query = {"department": student["department"], "semester": student["semester"]} if student else {"_id": None}

    slots = await timetable_collection.find(query).to_list(length=2000)
    subjects = await subjects_collection.find({"_id": {"$in": list({s["subject_id"] for s in slots})}}).to_list(length=2000)
    subjects_by_id = {s["_id"]: s for s in subjects}

    faculty_docs = await faculty_collection.find({"faculty_id": {"$in": list({s["faculty_id"] for s in slots})}}).to_list(length=2000)
    fac_users = await users_collection.find({"_id": {"$in": [f["user_id"] for f in faculty_docs]}}).to_list(length=2000)
    fac_user_by_id = {u["_id"]: u for u in fac_users}
    faculty_name = {f["faculty_id"]: fac_user_by_id.get(f["user_id"], {}).get("full_name") for f in faculty_docs}

    return [
        {
            "id": s["_id"], "day_of_week": s["day_of_week"],
            "start_time": s["start_time"], "end_time": s["end_time"], "classroom": s["classroom"],
            "subject_id": s["subject_id"],
            "subject_name": subjects_by_id.get(s["subject_id"], {}).get("name", "Subject"),
            "subject_code": subjects_by_id.get(s["subject_id"], {}).get("code"),
            "faculty_id": s["faculty_id"], "faculty_name": faculty_name.get(s["faculty_id"]),
            "department": s["department"], "semester": s["semester"],
        }
        for s in slots
    ]


@router.get("/my-schedule")
async def my_schedule(user=Depends(require_role("faculty", "student"))):
    """Weekly schedule for the logged-in user, built from whatever the Admin put in the timetable."""
    return {"slots": await schedule_slots_for_user(user)}
