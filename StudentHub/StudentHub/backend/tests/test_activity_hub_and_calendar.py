"""Faculty Classroom Activity Hub + Smart Calendar feed. Clock is pinned to Monday 12 Oct 2026, 11:00 so
'started / ended / pending' are deterministic."""
from datetime import datetime, timezone, timedelta

import pytest

from conftest import auth
from app import database as dbm
from app.services import faculty_subject_links as links

NOW = datetime(2026, 10, 12, 11, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))   # a Monday
TODAY = "2026-10-12"


@pytest.fixture(autouse=True)
def pinned_clock(monkeypatch):
    from app.routes import activity_hub, attendance
    monkeypatch.setattr(activity_hub, "local_now", lambda: NOW)
    monkeypatch.setattr(attendance, "local_today", lambda: NOW.date())      # attendance may not be marked for the future


async def hub(client, who):
    r = await client.get("/faculty/me/activity-hub", headers=auth(who))
    assert r.status_code == 200, r.text
    return r.json()


def task(data, key):
    return next(t for t in data["tasks"] if t["key"] == key)


async def add_slot(client, world, subject, faculty_id, day, start, end, room, sem=3):
    r = await client.post("/timetable", json={"day_of_week": day, "start_time": start, "end_time": end, "subject_id": world[subject]["_id"],
                                              "faculty_id": faculty_id, "classroom": room, "department": "Computer Science", "semester": sem},
                          headers=auth(world["admin"]))
    assert r.status_code == 201, r.text


async def test_roles_and_authentication(client, world):
    assert (await client.get("/faculty/me/activity-hub")).status_code == 401
    assert (await client.get("/faculty/me/activity-hub", headers={"Authorization": "Bearer junk"})).status_code == 401
    for who in ("admin", "alice"):
        assert (await client.get("/faculty/me/activity-hub", headers=auth(world[who]))).status_code == 403


async def test_no_classes_today_is_a_valid_empty_state(client, world):
    await add_slot(client, world, "ds", "1001", "Tuesday", "09:00", "10:00", "R1")        # not today
    d = await hub(client, world["f1"])
    assert d["classes"] == [] and d["summary"]["classes_today"] == 0 and d["summary"]["teaching_minutes_today"] == 0
    assert d["date"] == TODAY and d["weekday"] == "Monday" and d["assigned_subjects"] == 1
    # tasks are still real even with no class today: DS has 2 enrolled students and no marks yet
    assert task(d, "marks_to_enter")["count"] == 2
    assert task(d, "attendance")["count"] == 0


async def test_faculty_without_subjects_gets_zeros_not_errors(client, world):
    await dbm.faculty_subjects_collection.delete_many({"faculty_id": "1001"})
    d = await hub(client, world["f1"])
    assert d["assigned_subjects"] == 0 and d["classes"] == [] and all(t["count"] == 0 for t in d["tasks"])
    assert d["summary"]["tasks_outstanding"] == 0


async def test_todays_classes_numbering_status_and_isolation_between_faculty(client, world):
    await add_slot(client, world, "ds", "1001", "Monday", "14:00", "15:00", "R2")
    await add_slot(client, world, "ds", "1001", "Monday", "09:00", "10:00", "R1")          # inserted out of order on purpose
    await add_slot(client, world, "dbms", "1002", "Monday", "10:00", "11:00", "R3")
    await add_slot(client, world, "ds", "1001", "Wednesday", "09:00", "10:00", "R1")        # other weekday
    d1, d2 = await hub(client, world["f1"]), await hub(client, world["f2"])

    assert [(c["start_time"], c["lecture"], c["lectures_today"], c["classroom"]) for c in d1["classes"]] == [("09:00", 1, 2, "R1"), ("14:00", 2, 2, "R2")]
    assert [c["started"] for c in d1["classes"]] == [True, False] and [c["ended"] for c in d1["classes"]] == [True, False]
    assert d1["classes"][0]["subject_name"] == "Data Structures" and d1["classes"][0]["enrolled_students"] == 2
    assert d1["summary"]["classes_today"] == 2 and d1["summary"]["teaching_minutes_today"] == 120 and d1["summary"]["students_today"] == 2

    # faculty 2 sees only their own class, and nothing of faculty 1 leaks into either response
    assert [c["subject_name"] for c in d2["classes"]] == ["DBMS"] and d2["classes"][0]["started"] is True and d2["classes"][0]["ended"] is True
    assert "Data Structures" not in str(d2) and "Faculty One" not in str(d2)
    assert "DBMS" not in str(d1) and "Faculty Two" not in str(d1) and "Operating Systems" not in str(d1)
    assert "hashed_password" not in str(d1) and "alice@gmail.com" not in str(d1)       # no student private data


async def test_attendance_task_follows_real_attendance(client, world):
    await add_slot(client, world, "ds", "1001", "Monday", "09:00", "10:00", "R1")
    await add_slot(client, world, "ds", "1001", "Monday", "14:00", "15:00", "R1")          # same subject twice a day
    a, b = world["alice_doc"]["_id"], world["bob_doc"]["_id"]
    d = await hub(client, world["f1"])
    assert task(d, "attendance")["count"] == 1                                              # one SUBJECT outstanding (attendance is per subject/day)
    assert task(d, "attendance")["breakdown"] == [{"subject_id": world["ds"]["_id"], "subject_name": "Data Structures", "count": 1}]
    assert all(c["attendance"]["status"] == "pending" for c in d["classes"])

    mark = lambda entries: client.post("/attendance/mark", json={"subject_id": world["ds"]["_id"], "date": TODAY, "entries": entries}, headers=auth(world["f1"]))
    assert (await mark([{"student_id": a, "status": "present"}])).status_code == 200
    d = await hub(client, world["f1"])
    assert d["classes"][0]["attendance"] == {"status": "partial", "marked": 1, "enrolled": 2} and task(d, "attendance")["count"] == 1
    assert (await mark([{"student_id": b, "status": "absent"}])).status_code == 200
    d = await hub(client, world["f1"])
    assert all(c["attendance"]["status"] == "complete" for c in d["classes"]) and task(d, "attendance")["count"] == 0
    assert d["summary"]["attendance_subjects_started"] == 1 and d["summary"]["attendance_subjects_done"] == 1
    # attendance for a different DATE does not count as today's
    await dbm.attendance_collection.delete_many({})
    await mark([{"student_id": a, "status": "present"}, {"student_id": b, "status": "present"}])
    await dbm.attendance_collection.update_many({}, {"$set": {"date": "2026-10-05"}})
    assert task(await hub(client, world["f1"]), "attendance")["count"] == 1


async def test_a_class_that_has_not_started_is_not_an_attendance_task(client, world):
    await add_slot(client, world, "ds", "1001", "Monday", "14:00", "15:00", "R1")
    d = await hub(client, world["f1"])
    assert d["classes"][0]["started"] is False and task(d, "attendance")["count"] == 0


async def test_marks_tasks_update_as_marks_are_entered_and_published(client, world):
    ds = world["ds"]["_id"]; a, b = world["alice_doc"]["_id"], world["bob_doc"]["_id"]
    h = auth(world["f1"])
    d = await hub(client, world["f1"])
    assert (task(d, "marks_to_enter")["count"], task(d, "marks_to_publish")["count"]) == (2, 0)

    await client.put("/marks", json={"student_id": a, "subject_id": ds, "internal": 40}, headers=h)
    d = await hub(client, world["f1"])
    assert (task(d, "marks_to_enter")["count"], task(d, "marks_to_publish")["count"]) == (1, 1)
    await client.put("/marks", json={"student_id": b, "subject_id": ds, "practical": 30}, headers=h)
    d = await hub(client, world["f1"])
    assert (task(d, "marks_to_enter")["count"], task(d, "marks_to_publish")["count"]) == (0, 2)
    for rec in await dbm.marks_collection.find({"subject_id": ds}).to_list(10):
        assert (await client.put(f"/marks/{rec['_id']}/publish", headers=h)).status_code == 200
    d = await hub(client, world["f1"])
    assert (task(d, "marks_to_enter")["count"], task(d, "marks_to_publish")["count"]) == (0, 0)
    # a record holding no values at all does not count as "entered"
    await dbm.marks_collection.update_one({"student_id": a, "subject_id": ds}, {"$set": {"internal": None, "practical": None}})
    assert task(await hub(client, world["f1"]), "marks_to_enter")["count"] == 1
    # other faculty's marks are never counted here
    assert task(await hub(client, world["f2"]), "marks_to_publish")["count"] == 0


async def test_submission_and_doubt_tasks_and_readiness(client, world):
    ds = world["ds"]["_id"]; hf = auth(world["f1"]); ha = auth(world["alice"])
    due = (NOW.date() + timedelta(days=3)).isoformat()
    aid = (await client.post("/assignments", json={"title": "Trees", "description": "d", "subject_id": ds, "due_date": due}, headers=hf)).json()["id"]
    await client.post("/notes/upload", data={"title": "Unit 1", "subject_id": ds, "unit": "1"}, files={"file": ("n.pdf", b"%PDF-1.4 x", "application/pdf")}, headers=hf)
    await add_slot(client, world, "ds", "1001", "Monday", "14:00", "15:00", "R1")

    d = await hub(client, world["f1"])
    assert d["classes"][0]["readiness"] == {"notes_uploaded": 1, "open_assignments": 1, "submissions_to_review": 0}
    assert d["summary"]["assignments_due_this_week"] == 1 and task(d, "submissions_to_review")["count"] == 0

    assert (await client.post(f"/assignments/{aid}/submit", json={"file_url": "/uploads/x.pdf"}, headers=ha)).status_code == 200
    d = await hub(client, world["f1"])
    assert task(d, "submissions_to_review")["count"] == 1 and d["classes"][0]["readiness"]["submissions_to_review"] == 1
    sub = (await client.get(f"/assignments/{aid}/submissions", headers=hf)).json()[0]["id"]
    await client.put(f"/assignments/submissions/{sub}/grade", json={"grade": "A"}, headers=hf)
    assert task(await hub(client, world["f1"]), "submissions_to_review")["count"] == 0                     # graded -> task disappears

    q = await client.post("/doubts", json={"subject_id": ds, "question": "Why is a heap not a BST?"}, headers=ha)
    assert q.status_code == 201
    assert task(await hub(client, world["f1"]), "doubts_unanswered")["count"] == 1
    assert task(await hub(client, world["f2"]), "doubts_unanswered")["count"] == 0                        # another faculty's subject
    await client.put(f"/doubts/{q.json()['id']}/reply", json={"reply": "Different invariants."}, headers=hf)
    assert task(await hub(client, world["f1"]), "doubts_unanswered")["count"] == 0
    # an assignment due in the past is not "open"
    await dbm.assignments_collection.update_one({"_id": aid}, {"$set": {"due_date": "2026-10-01"}})
    d = await hub(client, world["f1"])
    assert d["classes"][0]["readiness"]["open_assignments"] == 0 and d["summary"]["assignments_due_this_week"] == 0


async def test_shared_subject_and_unassignment_are_reflected(client, world):
    ds = world["ds"]["_id"]
    await add_slot(client, world, "ds", "1001", "Monday", "09:00", "10:00", "R1")
    await links.add_links("1002", [ds])                                                     # f2 now co-teaches DS
    # students still needing marks for f2: DBMS (alice, bob) + DS (alice, bob) + OS (carol) = 5
    assert task(await hub(client, world["f2"]), "marks_to_enter")["count"] == 5
    names = {b["subject_name"] for b in task(await hub(client, world["f2"]), "marks_to_enter")["breakdown"]}
    assert {"Data Structures", "DBMS"} <= names

    # f1 is unassigned from DS -> everything about DS disappears from f1's hub, but not from f2's
    await client.delete(f"/faculty/{world['f1_doc']['_id']}/subjects/{ds}", headers=auth(world["admin"]))
    d1 = await hub(client, world["f1"])
    assert d1["classes"] == [] and d1["assigned_subjects"] == 0 and all(t["count"] == 0 for t in d1["tasks"])
    assert "Data Structures" in str(await hub(client, world["f2"]))


# ------------------------------------------------------------------ calendar feed

async def test_calendar_includes_only_the_users_own_lectures(client, world):
    await add_slot(client, world, "ds", "1001", "Monday", "09:00", "10:00", "R1")
    await add_slot(client, world, "dbms", "1002", "Tuesday", "11:00", "12:00", "R2")
    await add_slot(client, world, "os", "1002", "Friday", "13:00", "14:00", "R9", sem=5)
    cal = lambda who: client.get("/calendar/me", headers=auth(world[who]))
    f1 = (await cal("f1")).json(); f2 = (await cal("f2")).json(); alice = (await cal("alice")).json(); carol = (await cal("carol")).json(); adm = (await cal("admin")).json()
    assert [(c["subject_name"], c["day_of_week"]) for c in f1["weekly_classes"]] == [("Data Structures", "Monday")]
    assert {c["subject_name"] for c in f2["weekly_classes"]} == {"DBMS", "Operating Systems"}
    assert {c["subject_name"] for c in alice["weekly_classes"]} == {"Data Structures", "DBMS"}      # her class group (CS sem 3)
    assert {c["subject_name"] for c in carol["weekly_classes"]} == {"Operating Systems"}
    assert adm["weekly_classes"] == [] and "events" in adm
    assert "Faculty Two" not in str(f1["weekly_classes"]) and "DBMS" not in str(f1["weekly_classes"])
    assert (await client.get("/calendar/me")).status_code == 401


async def test_calendar_events_deadlines_and_leave_ranges_still_work(client, world):
    ds = world["ds"]["_id"]
    await client.post("/assignments", json={"title": "Graphs", "description": "d", "subject_id": ds, "due_date": "2026-10-20"}, headers=auth(world["f1"]))
    await dbm.leave_requests_collection.insert_one({"_id": "l1", "user_id": world["alice"]["_id"], "from_date": "2026-10-14", "to_date": "2026-10-16", "reason": "x", "status": "approved"})
    alice = (await client.get("/calendar/me", headers=auth(world["alice"]))).json()
    due = [e for e in alice["events"] if e["type"] == "assignment"]
    assert due and due[0]["date"] == "2026-10-20" and due[0]["title"] == "Graphs"
    leave = next(e for e in alice["events"] if e["type"] == "leave")
    assert (leave["date"], leave["end_date"]) == ("2026-10-14", "2026-10-16")
    f1 = (await client.get("/calendar/me", headers=auth(world["f1"]))).json()
    assert any(e["type"] == "assignment" and e["title"] == "Due: Graphs" for e in f1["events"])
    # faculty 2 teaches other subjects and must not see f1's assignment deadline
    f2 = (await client.get("/calendar/me", headers=auth(world["f2"]))).json()
    assert not any("Graphs" in e["title"] for e in f2["events"])
    # another student's leave is never in alice's calendar
    bob = (await client.get("/calendar/me", headers=auth(world["bob"]))).json()
    assert not any(e["type"] == "leave" for e in bob["events"])


async def test_removed_student_features_keep_their_backend_and_data(client, world):
    """The Student UI entries were removed, but backend APIs and stored data were deliberately kept."""
    from app.main import app
    paths = {r.path for r in app.routes}
    assert any(p.startswith("/focus") for p in paths) and any(p.startswith("/time-capsule") for p in paths) and any(p.startswith("/locker") for p in paths)
    assert (await client.get("/study-coach/plans", headers=auth(world["alice"]))).status_code == 200      # unrelated student features intact
    assert (await client.get("/ai/status", headers=auth(world["alice"]))).status_code == 200
