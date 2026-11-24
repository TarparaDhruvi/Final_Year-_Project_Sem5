"""Regression: the app's real demo seed data (what a fresh install contains) works with the new rules."""
from conftest import auth
from app import database as dbm
from app import database as dbm
from app.seed import seed_default_admin, seed_demo_data
from app.services.subject_sync import sync_faculty_subject_ids


async def test_demo_seed_flows_through_new_faculty_and_admin_endpoints(client):
    await seed_default_admin(); await seed_demo_data(); await sync_faculty_subject_ids()
    # real login flow with the documented demo credentials
    r = await client.post("/auth/login/faculty", json={"faculty_id": "1001", "email": "rohit.verma.faculty@gmail.com", "password": "Demo@12345"})
    assert r.status_code == 200, r.text
    hf = {"Authorization": f"Bearer {r.json()['access_token']}"}
    mine = (await client.get("/faculty/me/students", headers=hf)).json()
    assert len(mine) > 0 and all(s["subjects"] for s in mine)

    subj = (await client.get("/faculty/me/subjects", headers=hf)).json()[0]
    roster = (await client.get("/students/roster", params={"subject_id": subj["id"]}, headers=hf)).json()
    assert {s["id"] for s in roster} == {s["id"] for s in mine if any(x["id"] == subj["id"] for x in s["subjects"])}
    # marking the whole roster (what the existing Attendance page does) still works
    from datetime import date
    entries = [{"student_id": s["id"], "status": "present"} for s in roster]
    assert (await client.post("/attendance/mark", json={"subject_id": subj["id"], "date": date.today().isoformat(), "entries": entries}, headers=hf)).status_code == 200

    ra = await client.post("/auth/login/admin", json={"admin_id": "ADMIN001", "email": "admin@gmail.com", "password": "Admin@12345"})
    ha = {"Authorization": f"Bearer {ra.json()['access_token']}"}
    students = (await client.get("/students", headers=ha)).json()
    assert len(students) == 10
    detail = (await client.get(f"/students/{students[0]['id']}", headers=ha)).json()
    assert detail["academics"] and detail["email"].endswith("@gmail.com")

    rs = await client.post("/auth/login/student", json={"email": "demo.student1@gmail.com", "password": "Demo@12345"})
    assert rs.status_code == 200


async def test_simulated_restart_keeps_assignments_exactly(client):
    """Re-runs the startup sequence from main.py (migration -> seeds -> sync) on the same database, twice, as a
    backend restart would, after the Admin has made changes. Nothing may be lost, re-added or duplicated."""
    from app.seed import seed_default_admin, seed_demo_data
    from app.services import faculty_subject_links as links
    from app.services.subject_sync import sync_faculty_subject_ids

    async def startup():
        await links.migrate_legacy_assignments()
        await seed_default_admin(); await seed_demo_data(); await sync_faculty_subject_ids()

    await startup()
    ra = await client.post("/auth/login/admin", json={"admin_id": "ADMIN001", "email": "admin@gmail.com", "password": "Admin@12345"})
    ha = {"Authorization": f"Bearer {ra.json()['access_token']}"}
    faculty = (await client.get("/faculty", headers=ha)).json()
    a, b = faculty[0], faculty[1]
    shared = a["subject_ids"][0]

    # Admin gives A's first subject to B as well, then removes a different subject from A
    assert (await client.post(f"/faculty/{b['id']}/subjects", json={"subject_ids": [shared]}, headers=ha)).status_code in (200, 409)
    removed = a["subject_ids"][-1] if len(a["subject_ids"]) > 1 else None
    if removed:
        assert (await client.delete(f"/faculty/{a['id']}/subjects/{removed}", headers=ha)).status_code == 200

    def snapshot(rows):
        return {f["faculty_id"]: sorted(f["subject_ids"]) for f in rows}

    before = snapshot((await client.get("/faculty", headers=ha)).json())
    count_before = await dbm.faculty_subjects_collection.count_documents({})
    for _ in range(2):
        await startup()
    after = snapshot((await client.get("/faculty", headers=ha)).json())
    assert after == before
    assert await dbm.faculty_subjects_collection.count_documents({}) == count_before
    assert shared in after[a["faculty_id"]] and shared in after[b["faculty_id"]]          # still shared by both
    if removed:
        assert removed not in after[a["faculty_id"]]                                       # removal was not undone
    # no duplicate pairs
    pairs = [(l["faculty_id"], l["subject_id"]) for l in await dbm.faculty_subjects_collection.find({}).to_list(10000)]
    assert len(pairs) == len(set(pairs))


async def test_pre_upgrade_database_is_migrated_without_losing_the_old_assignments(client):
    """A database created by the previous version (single subjects.faculty_id, no link collection) keeps every
    teacher assignment after the upgrade, and the new many-to-many features then work on top of it."""
    from app.seed import seed_default_admin, seed_demo_data
    from app.services import faculty_subject_links as links
    from app.services.subject_sync import sync_faculty_subject_ids

    await seed_default_admin(); await seed_demo_data(); await sync_faculty_subject_ids()
    # rebuild the legacy shape from the seeded data: copy each link into subjects.faculty_id, then drop links + marker
    legacy = {}
    for l in await dbm.faculty_subjects_collection.find({}).to_list(10000):
        await dbm.subjects_collection.update_one({"_id": l["subject_id"]}, {"$set": {"faculty_id": l["faculty_id"]}})
        legacy[l["subject_id"]] = l["faculty_id"]
    await dbm.faculty_subjects_collection.delete_many({})
    await dbm.schema_migrations_collection.delete_many({})
    await dbm.faculty_collection.update_many({}, {"$set": {"subject_ids": []}})
    subjects_before = await dbm.subjects_collection.count_documents({})

    result = await links.migrate_legacy_assignments()
    await sync_faculty_subject_ids()
    assert result["migrated"] == len(legacy) and result["skipped"] is False
    assert {l["subject_id"]: l["faculty_id"] for l in await dbm.faculty_subjects_collection.find({}).to_list(10000)} == legacy
    assert await dbm.subjects_collection.count_documents({}) == subjects_before            # nothing deleted
    # the faculty portal still shows exactly what it showed before the upgrade
    rf = await client.post("/auth/login/faculty", json={"faculty_id": "1001", "email": "rohit.verma.faculty@gmail.com", "password": "Demo@12345"})
    hf = {"Authorization": f"Bearer {rf.json()['access_token']}"}
    mine = {s["id"] for s in (await client.get("/faculty/me/subjects", headers=hf)).json()}
    assert mine == {sid for sid, fid in legacy.items() if fid == "1001"} and mine
