"""Parts 2 + 3: many-to-many faculty↔subject assignment, and permissions that follow it."""
from datetime import date

import pytest

from conftest import auth
from app import database as dbm
from app.services import faculty_subject_links as links

TODAY = date.today().isoformat()


async def make_faculty(client, world, fid, name):
    r = await client.post("/faculty", json={"full_name": name, "email": f"{name.split()[0].lower()}.{fid}@gmail.com", "password": "Strong@123", "confirm_password": "Strong@123",
                                            "phone": "9000000000", "faculty_id": fid, "department": "Computer Science", "designation": "Lecturer"}, headers=auth(world["admin"]))
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def make_subject(client, world, name, code, sem=3):
    r = await client.post("/subjects", json={"name": name, "code": code, "department": "Computer Science", "semester": sem}, headers=auth(world["admin"]))
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def faculty_subjects(client, world, doc_id):
    rows = (await client.get("/faculty", headers=auth(world["admin"]))).json()
    return set(next(f for f in rows if f["id"] == doc_id)["subject_ids"])


async def subject_faculty(client, world, subject_id):
    rows = (await client.get("/subjects", headers=auth(world["admin"]))).json()
    return set(next(s for s in rows if s["id"] == subject_id)["faculty_ids"])


async def test_the_original_bug_java_stays_with_faculty_a_when_given_to_b(client, world):
    h = auth(world["admin"])
    a = await make_faculty(client, world, "201", "Teacher A")
    b = await make_faculty(client, world, "202", "Teacher B")
    c = await make_faculty(client, world, "203", "Teacher C")
    java = await make_subject(client, world, "Java", "JV101")
    python_id = await make_subject(client, world, "Python", "PY101")
    other = await make_subject(client, world, "Networks", "NW101")

    assert (await client.put(f"/faculty/{a}/assign-subjects", json={"subject_ids": [java]}, headers=h)).status_code == 200
    assert (await client.put(f"/faculty/{b}/assign-subjects", json={"subject_ids": [java]}, headers=h)).status_code == 200
    # ← previously this wiped Java from A
    assert await faculty_subjects(client, world, a) == {java}
    assert await faculty_subjects(client, world, b) == {java}
    assert (await client.put(f"/faculty/{c}/assign-subjects", json={"subject_ids": [java]}, headers=h)).status_code == 200
    assert await subject_faculty(client, world, java) == {"201", "202", "203"}

    # several subjects for one faculty member
    assert (await client.put(f"/faculty/{a}/assign-subjects", json={"subject_ids": [java, python_id, other]}, headers=h)).status_code == 200
    assert await faculty_subjects(client, world, a) == {java, python_id, other}
    assert await faculty_subjects(client, world, b) == {java} and await faculty_subjects(client, world, c) == {java}

    # remove Java from A only
    assert (await client.delete(f"/faculty/{a}/subjects/{java}", headers=h)).status_code == 200
    assert await faculty_subjects(client, world, a) == {python_id, other}
    assert await subject_faculty(client, world, java) == {"202", "203"}      # B and C keep it

    # replacing A's whole list never touches B or C either
    await client.put(f"/faculty/{a}/assign-subjects", json={"subject_ids": []}, headers=h)
    assert await faculty_subjects(client, world, a) == set()
    assert await faculty_subjects(client, world, b) == {java} and await faculty_subjects(client, world, c) == {java}


async def test_add_endpoint_is_additive_and_duplicates_are_rejected(client, world):
    h = auth(world["admin"])
    a = await make_faculty(client, world, "301", "Add Teacher")
    java, py = await make_subject(client, world, "Java", "JV1"), await make_subject(client, world, "Python", "PY1")
    assert (await client.post(f"/faculty/{a}/subjects", json={"subject_ids": [java]}, headers=h)).status_code == 200
    r = await client.post(f"/faculty/{a}/subjects", json={"subject_ids": [java, py]}, headers=h)
    assert r.status_code == 200 and r.json()["added"] == [py] and r.json()["already_assigned"] == [java]
    assert await faculty_subjects(client, world, a) == {java, py}
    dup = await client.post(f"/faculty/{a}/subjects", json={"subject_ids": [java]}, headers=h)
    assert dup.status_code == 409
    assert await dbm.faculty_subjects_collection.count_documents({"faculty_id": "301"}) == 2   # no duplicate rows
    assert (await client.post(f"/faculty/{a}/subjects", json={"subject_ids": []}, headers=h)).status_code == 422
    assert (await client.post(f"/faculty/{a}/subjects", json={"subject_ids": ["nope"]}, headers=h)).status_code == 400
    assert (await client.post("/faculty/missing/subjects", json={"subject_ids": [java]}, headers=h)).status_code == 404


async def test_unique_index_blocks_duplicate_pair_but_allows_many_teachers(client, world):
    from pymongo.errors import DuplicateKeyError
    sid = world["ds"]["_id"]
    await dbm.faculty_subjects_collection.insert_one({"_id": "x1", "faculty_id": "1002", "subject_id": sid})    # 2nd teacher: allowed
    with pytest.raises(DuplicateKeyError):
        await dbm.faculty_subjects_collection.insert_one({"_id": "x2", "faculty_id": "1002", "subject_id": sid})   # same pair: refused


async def test_remove_many_reassign_and_validation(client, world):
    h = auth(world["admin"])
    a, b = await make_faculty(client, world, "401", "Alpha One"), await make_faculty(client, world, "402", "Beta Two")
    s1 = await make_subject(client, world, "S1", "S1X")
    s2 = await make_subject(client, world, "S2", "S2X")
    s3 = await make_subject(client, world, "S3", "S3X")
    await client.put(f"/faculty/{a}/assign-subjects", json={"subject_ids": [s1, s2, s3]}, headers=h)
    await client.put(f"/faculty/{b}/assign-subjects", json={"subject_ids": [s1]}, headers=h)

    r = await client.post(f"/faculty/{a}/subjects/remove", json={"subject_ids": [s2, s3]}, headers=h)
    assert r.status_code == 200 and set(r.json()["removed"]) == {s2, s3}
    assert await faculty_subjects(client, world, a) == {s1}
    assert (await client.post(f"/faculty/{a}/subjects/remove", json={"subject_ids": [s2]}, headers=h)).status_code == 404   # not assigned any more
    assert (await client.delete(f"/faculty/{a}/subjects/{s2}", headers=h)).status_code == 404

    # reassign s1 from A to a third faculty C; B (co-teacher) is unaffected
    c = await make_faculty(client, world, "403", "Gamma Three")
    r = await client.post(f"/faculty/{a}/subjects/{s1}/reassign", json={"to_faculty_id": "403"}, headers=h)
    assert r.status_code == 200
    assert await subject_faculty(client, world, s1) == {"402", "403"}
    assert (await client.post(f"/faculty/{a}/subjects/{s1}/reassign", json={"to_faculty_id": "403"}, headers=h)).status_code == 404   # A no longer has it
    assert (await client.post(f"/faculty/{b}/subjects/{s1}/reassign", json={"to_faculty_id": "402"}, headers=h)).status_code == 400   # to self
    assert (await client.post(f"/faculty/{b}/subjects/{s1}/reassign", json={"to_faculty_id": "999"}, headers=h)).status_code == 404
    # reassign to someone who already teaches it just removes the source (no duplicate pair)
    assert (await client.post(f"/faculty/{b}/subjects/{s1}/reassign", json={"to_faculty_id": "403"}, headers=h)).status_code == 200
    assert await subject_faculty(client, world, s1) == {"403"}
    assert await dbm.faculty_subjects_collection.count_documents({"subject_id": s1}) == 1


async def test_subject_form_endpoints_multi_faculty(client, world):
    h = auth(world["admin"])
    r = await client.post("/subjects", json={"name": "Java", "code": "JV9", "department": "Computer Science", "semester": 3, "faculty_ids": ["1001", "1002"]}, headers=h)
    sid = r.json()["id"]
    assert await subject_faculty(client, world, sid) == {"1001", "1002"}
    # legacy single faculty_id on update is additive
    await client.put(f"/subjects/{sid}", json={"faculty_id": "1001"}, headers=h)
    assert await subject_faculty(client, world, sid) == {"1001", "1002"}
    await client.put(f"/subjects/{sid}", json={"faculty_ids": ["1002"]}, headers=h)                     # exact set
    assert await subject_faculty(client, world, sid) == {"1002"}
    assert (await client.post("/subjects", json={"name": "X", "code": "JV10", "department": "Computer Science", "semester": 3, "faculty_ids": ["nobody"]}, headers=h)).status_code == 400
    assert (await client.put(f"/subjects/{sid}", json={"faculty_ids": ["nobody"]}, headers=h)).status_code == 400
    listing = (await client.get("/subjects", headers=h)).json()
    java = next(s for s in listing if s["id"] == sid)
    assert "faculty_id" not in java and java["faculty"][0]["full_name"] == "Faculty Two"
    # faculty list for one subject + overview in both directions
    assert [f["faculty_id"] for f in (await client.get(f"/subjects/{sid}/faculty", headers=h)).json()] == ["1002"]
    ov = (await client.get("/faculty/assignments", headers=h)).json()
    assert {f["faculty_id"] for f in next(s for s in ov["by_subject"] if s["id"] == sid)["faculty"]} == {"1002"}
    assert sid in {x["id"] for x in next(f for f in ov["by_faculty"] if f["faculty_id"] == "1002")["subjects"]}


async def test_deleting_faculty_or_subject_only_removes_links(client, world):
    h = auth(world["admin"])
    sid = world["ds"]["_id"]
    await links.add_links("1002", [sid])           # DS now taught by 1001 AND 1002
    f1 = world["f1_doc"]["_id"]
    assert (await client.delete(f"/faculty/{f1}", headers=h)).status_code == 200
    assert await dbm.subjects_collection.find_one({"_id": sid})                   # subject survives
    assert await links.faculty_ids_for_subject(sid) == ["1002"]                   # co-teacher survives
    assert (await client.delete(f"/subjects/{sid}", headers=h)).status_code == 200
    assert await dbm.faculty_subjects_collection.count_documents({"subject_id": sid}) == 0


async def test_non_admin_cannot_change_assignments(client, world):
    f2 = world["f2_doc"]["_id"]; sid = world["ds"]["_id"]
    calls = [("PUT", f"/faculty/{f2}/assign-subjects", {"subject_ids": [sid]}), ("POST", f"/faculty/{f2}/subjects", {"subject_ids": [sid]}),
             ("POST", f"/faculty/{f2}/subjects/remove", {"subject_ids": [sid]}), ("DELETE", f"/faculty/{f2}/subjects/{sid}", None),
             ("POST", f"/faculty/{f2}/subjects/{sid}/reassign", {"to_faculty_id": "1001"}), ("GET", "/faculty/assignments", None),
             ("GET", f"/subjects/{sid}/faculty", None), ("POST", "/subjects", {"name": "x", "code": "Z", "department": "d", "semester": 1}),
             ("PUT", f"/subjects/{sid}", {"faculty_ids": []}), ("DELETE", f"/subjects/{sid}", None)]
    for who in ("f1", "alice"):
        for m, p, b in calls:
            assert (await client.request(m, p, json=b, headers=auth(world[who]))).status_code == 403, (who, m, p)
    for m, p, b in calls:
        assert (await client.request(m, p, json=b)).status_code == 401
    assert await links.faculty_ids_for_subject(sid) == ["1001"]


# -------------------------------------------------- Part 3: portals follow assignments

async def test_faculty_portal_follows_assignments_immediately(client, world):
    h1 = auth(world["f1"]); sid = world["ds"]["_id"]; admin = auth(world["admin"])
    mine = lambda: client.get("/faculty/me/subjects", headers=h1)
    assert [s["name"] for s in (await mine()).json()] == ["Data Structures"]
    f1 = world["f1_doc"]["_id"]
    await client.post(f"/faculty/{f1}/subjects", json={"subject_ids": [world["dbms"]["_id"]]}, headers=admin)
    assert {s["name"] for s in (await mine()).json()} == {"Data Structures", "DBMS"}
    assert all("faculty_id" not in s for s in (await mine()).json())
    await client.delete(f"/faculty/{f1}/subjects/{sid}", headers=admin)
    assert [s["name"] for s in (await mine()).json()] == ["DBMS"]


async def test_two_teachers_can_both_operate_on_a_shared_subject_and_lose_access_on_removal(client, world):
    admin = auth(world["admin"]); ds = world["ds"]["_id"]; alice = world["alice_doc"]["_id"]
    await links.add_links("1002", [ds])                                             # DS: 1001 + 1002
    mark = lambda who: client.post("/attendance/mark", json={"subject_id": ds, "date": TODAY, "entries": [{"student_id": alice, "status": "present"}]}, headers=auth(world[who]))
    assert (await mark("f1")).status_code == 200 and (await mark("f2")).status_code == 200
    assert (await client.put("/marks", json={"student_id": alice, "subject_id": ds, "internal": 40}, headers=auth(world["f2"]))).status_code == 200
    assert len((await client.get("/faculty/me/students", params={"subject_id": ds}, headers=auth(world["f2"]))).json()) == 2

    # remove f1 from DS: f1 is locked out, f2 isn't, and the history is untouched
    await client.delete(f"/faculty/{world['f1_doc']['_id']}/subjects/{ds}", headers=admin)
    assert (await mark("f1")).status_code == 403
    assert (await client.get(f"/attendance/subject/{ds}", headers=auth(world["f1"]))).status_code == 403
    assert (await client.put("/marks", json={"student_id": alice, "subject_id": ds, "internal": 1}, headers=auth(world["f1"]))).status_code == 403
    assert (await client.get(f"/marks/subject/{ds}", headers=auth(world["f1"]))).status_code == 403
    assert (await client.get("/faculty/me/students", params={"subject_id": ds}, headers=auth(world["f1"]))).status_code == 403
    assert (await mark("f2")).status_code == 200
    assert await dbm.attendance_collection.count_documents({"subject_id": ds}) == 1      # one row per student/day, preserved
    assert (await dbm.marks_collection.find_one({"subject_id": ds}))["internal"] == 40    # marks kept
    # the student still sees their own records
    assert (await client.get("/attendance/me", headers=auth(world["alice"]))).json()[0]["percentage"] == 100.0


async def test_notes_assignments_doubts_use_links(client, world):
    ds = world["ds"]["_id"]; admin = auth(world["admin"])
    await links.add_links("1002", [ds])
    pdf = b"%PDF-1.4 test"
    up = lambda who: client.post("/notes/upload", data={"title": "T", "subject_id": ds, "unit": "1"}, files={"file": ("n.pdf", pdf, "application/pdf")}, headers=auth(world[who]))
    assert (await up("f1")).status_code == 201 and (await up("f2")).status_code == 201
    asg = lambda who: client.post("/assignments", json={"title": "A", "description": "d", "subject_id": ds, "due_date": "2099-01-01"}, headers=auth(world[who]))
    assert (await asg("f1")).status_code == 201 and (await asg("f2")).status_code == 201
    # a faculty member who does NOT teach DS is refused everywhere
    assert (await client.post("/faculty/" + world["f2_doc"]["_id"] + "/subjects/" + ds + "/reassign", json={"to_faculty_id": "1001"}, headers=admin)).status_code == 200
    assert (await up("f2")).status_code == 403 and (await asg("f2")).status_code == 403

    # doubts: both teachers get notified, and only teachers of the subject may reply
    await links.add_links("1002", [ds])
    d = await client.post("/doubts", json={"subject_id": ds, "question": "What is a heap exactly?"}, headers=auth(world["alice"]))
    assert d.status_code == 201
    for fac in ("f1", "f2"):
        assert await dbm.notifications_collection.count_documents({"user_id": world[fac]["_id"], "title": "New Anonymous Doubt"}) == 1
    await dbm.faculty_subjects_collection.delete_many({"faculty_id": "1002", "subject_id": ds})
    assert (await client.put(f"/doubts/{d.json()['id']}/reply", json={"reply": "A heap is…"}, headers=auth(world["f2"]))).status_code == 403
    assert (await client.put(f"/doubts/{d.json()['id']}/reply", json={"reply": "A heap is…"}, headers=auth(world["f1"]))).status_code == 200


async def test_timetable_requires_assigned_teacher_and_follows_unassignment(client, world):
    admin = auth(world["admin"]); ds, dbms = world["ds"]["_id"], world["dbms"]["_id"]
    slot = {"day_of_week": "Monday", "start_time": "09:00", "end_time": "10:00", "subject_id": ds, "faculty_id": "1001",
            "classroom": "R1", "department": "Computer Science", "semester": 3}
    assert (await client.post("/timetable", json={**slot, "faculty_id": "1002"}, headers=admin)).status_code == 400   # 1002 doesn't teach DS
    assert (await client.post("/timetable", json={**slot, "subject_id": "ghost"}, headers=admin)).status_code == 404
    r = await client.post("/timetable", json=slot, headers=admin)
    assert r.status_code == 201, r.text
    sched = lambda who: client.get("/timetable/my-schedule", headers=auth(world[who]))
    assert len((await sched("f1")).json()["slots"]) == 1 and len((await sched("alice")).json()["slots"]) == 1
    await links.add_links("1002", [ds])                                              # shared subject: second teacher can be timetabled too
    assert (await client.post("/timetable", json={**slot, "faculty_id": "1002", "start_time": "11:00", "end_time": "12:00", "classroom": "R2", "semester": 3}, headers=admin)).status_code == 201
    await client.delete(f"/faculty/{world['f1_doc']['_id']}/subjects/{ds}", headers=admin)
    assert (await sched("f1")).json()["slots"] == []                                  # no longer teaches DS → drops off their schedule
    assert len((await sched("f2")).json()["slots"]) == 1


async def test_students_see_their_own_class_subjects_and_nobody_elses(client, world):
    # student-facing subject list is unchanged, and carries no private data
    rows = (await client.get("/subjects", params={"department": "Computer Science", "semester": 3}, headers=auth(world["alice"]))).json()
    assert {r["name"] for r in rows} == {"Data Structures", "DBMS"}
    assert all("hashed_password" not in str(r) for r in rows)
    # AI endpoints are still student-only
    assert (await client.get("/ai/status", headers=auth(world["f1"]))).status_code == 403
    assert (await client.get("/ai/status", headers=auth(world["admin"]))).status_code == 403
    assert (await client.get("/ai/status", headers=auth(world["alice"]))).status_code == 200


# -------------------------------------------------- migration safety

async def test_legacy_migration_is_one_time_nondestructive_and_persists(client, world):
    # simulate a pre-upgrade database: legacy single faculty_id on subjects, no links, no migration marker
    await dbm.faculty_subjects_collection.delete_many({})
    await dbm.schema_migrations_collection.delete_many({})
    await dbm.subjects_collection.update_one({"_id": world["ds"]["_id"]}, {"$set": {"faculty_id": "1001"}})
    await dbm.subjects_collection.update_one({"_id": world["dbms"]["_id"]}, {"$set": {"faculty_id": "1002"}})
    await dbm.subjects_collection.update_one({"_id": world["os"]["_id"]}, {"$set": {"faculty_id": "ghost-id"}})   # dangling legacy ref

    first = await links.migrate_legacy_assignments()
    assert first == {"skipped": False, "migrated": 2}
    assert await links.faculty_ids_for_subject(world["ds"]["_id"]) == ["1001"]
    assert await links.faculty_ids_for_subject(world["os"]["_id"]) == []              # dangling reference ignored, not crashed on
    legacy_still_there = await dbm.subjects_collection.find_one({"_id": world["ds"]["_id"]})
    assert legacy_still_there["faculty_id"] == "1001"                                  # nothing deleted or rewritten

    # "restart": migration again is a no-op; an admin removal made after migration must NOT be undone by stale legacy data
    admin = auth(world["admin"])
    await client.delete(f"/faculty/{world['f1_doc']['_id']}/subjects/{world['ds']['_id']}", headers=admin)
    again = await links.migrate_legacy_assignments()
    assert again["skipped"] is True
    from app.services.subject_sync import sync_faculty_subject_ids
    await sync_faculty_subject_ids()
    assert await links.faculty_ids_for_subject(world["ds"]["_id"]) == []
    # denormalised faculty.subject_ids matches the link collection
    f2 = await dbm.faculty_collection.find_one({"faculty_id": "1002"})
    assert set(f2["subject_ids"]) == {world["dbms"]["_id"]}
    # legacy subject output never leaks the stale field
    listing = (await client.get("/subjects", headers=admin)).json()
    assert all("faculty_id" not in s for s in listing)


async def test_race_safe_add_links(client, world):
    import asyncio
    sid = world["os"]["_id"]
    await asyncio.gather(*[links.add_links("1001", [sid]) for _ in range(6)])
    assert await dbm.faculty_subjects_collection.count_documents({"faculty_id": "1001", "subject_id": sid}) == 1
