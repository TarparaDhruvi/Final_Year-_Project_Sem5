"""
services/faculty_subject_links.py
The ONE source of truth for "who teaches what": the `faculty_subjects` collection, one document per
(faculty_id, subject_id) pair, unique on the pair.

Why the old design was wrong: `subjects.faculty_id` held a single teacher, and "assign subjects to faculty B"
did `update_many({_id in wanted}, {faculty_id: B})` — silently overwriting faculty A. Every operation here
touches ONLY the pairs it names, so assigning a subject to B can never remove it from A.

Removing a link never deletes marks, attendance, notes, assignments or submissions — those are keyed by
subject_id and stay in MongoDB as historical records.
"""
import uuid
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.database import faculty_subjects_collection, subjects_collection, faculty_collection, schema_migrations_collection

MIGRATION_ID = "faculty_subjects_many_to_many_v1"


def _link(faculty_id: str, subject_id: str, assigned_by: str | None) -> dict:
    return {"_id": str(uuid.uuid4()), "faculty_id": faculty_id, "subject_id": subject_id,
            "assigned_by": assigned_by, "created_at": datetime.now(timezone.utc)}


async def subject_ids_for_faculty(faculty_id: str) -> list[str]:
    links = await faculty_subjects_collection.find({"faculty_id": faculty_id}).to_list(length=5000)
    return [l["subject_id"] for l in links]


async def faculty_ids_for_subject(subject_id: str) -> list[str]:
    links = await faculty_subjects_collection.find({"subject_id": subject_id}).to_list(length=5000)
    return [l["faculty_id"] for l in links]


async def is_assigned(faculty_id: str, subject_id: str) -> bool:
    return await faculty_subjects_collection.find_one({"faculty_id": faculty_id, "subject_id": subject_id}) is not None


async def subjects_for_faculty(faculty_id: str) -> list[dict]:
    ids = await subject_ids_for_faculty(faculty_id)
    if not ids:
        return []
    return await subjects_collection.find({"_id": {"$in": ids}}).sort("name", 1).to_list(length=5000)


async def add_links(faculty_id: str, subject_ids: list[str], assigned_by: str | None = None) -> tuple[list[str], list[str]]:
    """Adds pairs; returns (newly_added, already_assigned). Idempotent and race-safe (the unique index is the backstop)."""
    added, existing = [], []
    for sid in dict.fromkeys(subject_ids):
        if await is_assigned(faculty_id, sid):
            existing.append(sid)
            continue
        try:
            await faculty_subjects_collection.insert_one(_link(faculty_id, sid, assigned_by))
            added.append(sid)
        except DuplicateKeyError:
            existing.append(sid)
    await sync_denormalised()
    return added, existing


async def add_links_for_subject(subject_id: str, faculty_ids: list[str], assigned_by: str | None = None) -> list[str]:
    """Adds teachers to ONE subject without touching existing teachers. Returns the newly added faculty IDs."""
    added = []
    for fid in dict.fromkeys(faculty_ids):
        a, _ = await add_links(fid, [subject_id], assigned_by)
        added += a and [fid]
    return added


async def remove_links(faculty_id: str, subject_ids: list[str]) -> int:
    result = await faculty_subjects_collection.delete_many({"faculty_id": faculty_id, "subject_id": {"$in": list(subject_ids)}})
    await sync_denormalised()
    return result.deleted_count


async def replace_for_faculty(faculty_id: str, subject_ids: list[str], assigned_by: str | None = None) -> tuple[list[str], list[str]]:
    """Make THIS faculty member's subject list exactly `subject_ids`. Other faculty are never touched.
    Returns (added, removed)."""
    wanted = list(dict.fromkeys(subject_ids))
    current = set(await subject_ids_for_faculty(faculty_id))
    to_remove = [s for s in current if s not in set(wanted)]
    if to_remove:
        await faculty_subjects_collection.delete_many({"faculty_id": faculty_id, "subject_id": {"$in": to_remove}})
    added, _ = await add_links(faculty_id, [s for s in wanted if s not in current], assigned_by)
    await sync_denormalised()
    return added, to_remove


async def replace_for_subject(subject_id: str, faculty_ids: list[str], assigned_by: str | None = None) -> tuple[list[str], list[str]]:
    """Make THIS subject's teacher list exactly `faculty_ids`. Other subjects are never touched."""
    wanted = list(dict.fromkeys(faculty_ids))
    current = set(await faculty_ids_for_subject(subject_id))
    to_remove = [f for f in current if f not in set(wanted)]
    if to_remove:
        await faculty_subjects_collection.delete_many({"subject_id": subject_id, "faculty_id": {"$in": to_remove}})
    added = []
    for fid in wanted:
        if fid not in current:
            try:
                await faculty_subjects_collection.insert_one(_link(fid, subject_id, assigned_by))
                added.append(fid)
            except DuplicateKeyError:
                pass
    await sync_denormalised()
    return added, to_remove


async def remove_all_for_faculty(faculty_id: str) -> None:
    await faculty_subjects_collection.delete_many({"faculty_id": faculty_id})
    await sync_denormalised()


async def remove_all_for_subject(subject_id: str) -> None:
    await faculty_subjects_collection.delete_many({"subject_id": subject_id})
    await sync_denormalised()


async def sync_denormalised() -> None:
    """Keeps `faculty.subject_ids` (a read-optimised copy used by announcements) equal to the link collection."""
    links = await faculty_subjects_collection.find({}).to_list(length=100000)
    by_faculty: dict[str, list[str]] = {}
    for l in links:
        by_faculty.setdefault(l["faculty_id"], []).append(l["subject_id"])
    async for f in faculty_collection.find({}):
        wanted = by_faculty.get(f["faculty_id"], [])
        if set(wanted) != set(f.get("subject_ids", [])):
            await faculty_collection.update_one({"_id": f["_id"]}, {"$set": {"subject_ids": wanted}})


async def migrate_legacy_assignments() -> dict:
    """ONE-TIME, non-destructive: turn each legacy `subjects.faculty_id` into a link pair.
    A marker document makes it run exactly once, so later removals are never "re-added" from stale legacy
    values on restart. Running it again is a harmless no-op. Nothing is deleted or modified on subjects."""
    if await schema_migrations_collection.find_one({"_id": MIGRATION_ID}):
        return {"skipped": True, "migrated": 0}
    migrated = 0
    legacy = await subjects_collection.find({"faculty_id": {"$nin": [None, ""]}}).to_list(length=100000)
    for s in legacy:
        if not await faculty_collection.find_one({"faculty_id": s["faculty_id"]}):
            continue   # dangling legacy reference: nothing sensible to link
        added, _ = await add_links(s["faculty_id"], [s["_id"]], assigned_by="migration")
        migrated += len(added)
    await schema_migrations_collection.insert_one(
        {"_id": MIGRATION_ID, "applied_at": datetime.now(timezone.utc), "migrated": migrated})
    return {"skipped": False, "migrated": migrated}
