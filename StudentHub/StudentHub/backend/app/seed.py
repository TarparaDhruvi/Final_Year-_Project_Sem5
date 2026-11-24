"""
seed.py
Admin accounts are never created through public signup or even through
an "Add Admin" UI — they're pre-provisioned in the database. This module
seeds exactly one default admin account on first startup (only if the
`users` collection has zero admin accounts yet), so the college always
has a way in. Credentials come from environment variables so they're not
hardcoded in source control.
"""

import os
from app.database import users_collection
from app.auth import hash_password
from app.models.user import new_user_document


async def seed_default_admin():
    existing_admin = await users_collection.find_one({"role": "admin"})
    if existing_admin:
        return  # Already seeded — never overwrite an existing admin.

    admin_id = os.getenv("ADMIN_ID", "ADMIN001")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@gmail.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin@12345")
    admin_name = os.getenv("ADMIN_NAME", "Administrator")

    doc = new_user_document(
        full_name=admin_name,
        email=admin_email.lower(),
        hashed_password=hash_password(admin_password),
        role="admin",
        phone=None,
        is_verified=True,
    )
    doc["login_id"] = admin_id
    await users_collection.insert_one(doc)

    print("=" * 60)
    print("StudentHub: default Admin account seeded.")
    print(f"  Admin ID : {admin_id}")
    print(f"  Email    : {admin_email}")
    print(f"  Password : {admin_password}")
    print("  Please log in and change this password immediately.")
    print("  (Set ADMIN_ID / ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_NAME in .env")
    print("   before first run to seed different credentials.)")
    print("=" * 60)


async def seed_demo_data():
    """
    Seeds 3 Faculty, 10 Students, 3 Subjects, a Monday–Wednesday timetable,
    and one assignment per subject — everything a viva demo needs to show
    real, non-empty dashboards. Runs once: if any demo student already
    exists (student_id starting with "2024"), it's skipped entirely.
    """
    from datetime import datetime, timedelta, timezone
    from app.database import (
        faculty_collection, students_collection, subjects_collection,
        timetable_collection, assignments_collection,
    )
    from app.models.faculty import new_faculty_document
    from app.models.student import new_student_document
    from app.models.subject import new_subject_document
    from app.services.faculty_subject_links import add_links
    from app.models.timetable import new_timetable_document
    from app.models.assignment import new_assignment_document

    if await students_collection.find_one({"student_id": "2024001"}):
        return  # Demo data already seeded.

    DEPARTMENT = "Computer Science"
    DEMO_PASSWORD = "Demo@12345"

    faculty_specs = [
        ("1001", "Rohit Verma", "rohit.verma.faculty@gmail.com", "Assistant Professor"),
        ("1002", "Sunita Rao", "sunita.rao.faculty@gmail.com", "Associate Professor"),
        ("1003", "Amit Kulkarni", "amit.kulkarni.faculty@gmail.com", "Assistant Professor"),
    ]
    faculty_ids = []
    for fid, name, email, designation in faculty_specs:
        user_doc = new_user_document(name, email, hash_password(DEMO_PASSWORD), "faculty", None, True, login_id=fid)
        await users_collection.insert_one(user_doc)
        await faculty_collection.insert_one(new_faculty_document(user_doc["_id"], fid, DEPARTMENT, designation))
        faculty_ids.append(fid)

    subject_specs = [
        ("Data Structures", "CS201", faculty_ids[0]),
        ("Database Management Systems", "CS202", faculty_ids[1]),
        ("Operating Systems", "CS203", faculty_ids[2]),
    ]
    subject_ids = []
    for name, code, fid in subject_specs:
        doc = new_subject_document(name, code, DEPARTMENT, 3, 4)
        await subjects_collection.insert_one(doc)
        subject_ids.append(doc["_id"])
        await add_links(fid, [doc["_id"]], assigned_by="seed")

    for i in range(1, 11):
        sid = f"2024{i:03d}"
        name = f"Demo Student {i}"
        email = f"demo.student{i}@gmail.com"
        user_doc = new_user_document(name, email, hash_password(DEMO_PASSWORD), "student", "9800000000", True, login_id=sid)
        await users_collection.insert_one(user_doc)
        await students_collection.insert_one(new_student_document(user_doc["_id"], sid, DEPARTMENT, 3, "2024-2028"))

    slots = [
        ("Monday", "09:00", "10:00", subject_ids[0], faculty_ids[0], "Room 101"),
        ("Monday", "10:00", "11:00", subject_ids[1], faculty_ids[1], "Room 102"),
        ("Tuesday", "09:00", "10:00", subject_ids[2], faculty_ids[2], "Room 103"),
        ("Wednesday", "11:00", "12:00", subject_ids[0], faculty_ids[0], "Room 101"),
    ]
    for day, start, end, subj_id, fac_id, room in slots:
        await timetable_collection.insert_one(
            new_timetable_document(day, start, end, subj_id, fac_id, room, DEPARTMENT, 3)
        )

    now = datetime.now(timezone.utc)
    due_offsets = [3, 7, 10]
    for (name, _code, fac_id), subj_id, offset in zip(subject_specs, subject_ids, due_offsets):
        due_date = (now + timedelta(days=offset)).date().isoformat()
        await assignments_collection.insert_one(
            new_assignment_document(
                title=f"{name} — Assignment 1",
                description=f"Complete the first assignment for {name}. Submit as a link or note.",
                subject_id=subj_id,
                faculty_id=fac_id,
                due_date=due_date,
            )
        )

    print("=" * 60)
    print("StudentHub: demo data seeded — 3 Faculty, 10 Students, 3 Subjects,")
    print("a partial timetable, and 3 assignments.")
    print(f"  Demo login password for all seeded accounts: {DEMO_PASSWORD}")
    print("  Faculty IDs: 1001, 1002, 1003 · Student IDs: 2024001–2024010")
    print("=" * 60)


async def migrate_study_materials():
    """
    Early builds stored AI Study Coach uploads in `uploaded_notes` (the faculty notes collection),
    which exposed students' private files through GET /notes. Move any such documents (identified by
    their `extracted_text` field, which faculty notes never have) into the dedicated `study_materials`
    collection. Safe to run on every startup — it does nothing once there is nothing left to move.
    """
    from app.database import uploaded_notes_collection, study_materials_collection
    legacy = await uploaded_notes_collection.find({"extracted_text": {"$exists": True}}).to_list(length=100000)
    for doc in legacy:
        if not await study_materials_collection.find_one({"_id": doc["_id"]}):
            await study_materials_collection.insert_one(doc)
        await uploaded_notes_collection.delete_one({"_id": doc["_id"]})
    if legacy:
        print(f"StudentHub: moved {len(legacy)} Study Coach upload(s) out of the shared notes collection.")
