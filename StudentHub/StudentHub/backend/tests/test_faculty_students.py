"""Priority 5 + 3/authorization: Faculty can only see/act on students in THEIR subjects; Admin stays institution-wide."""
from datetime import date, timedelta

import pytest

from conftest import auth
from app import database as dbm

TODAY = date.today().isoformat()


async def ids(client, who, **params):
    r = await client.get("/faculty/me/students", params=params, headers=auth(who))
    assert r.status_code == 200, r.text
    return {x["student_id"] for x in r.json()}


async def test_faculty_sees_only_students_of_assigned_subjects(client, world):
    assert await ids(client, world["f1"]) == {"2024001", "2024002"}                  # DS = CS sem3
    assert await ids(client, world["f2"]) == {"2024001", "2024002", "2024003"}       # DBMS CS sem3 + OS CS sem5
    # dave (IT) belongs to nobody's class
    assert "2024004" not in await ids(client, world["f1"]) | await ids(client, world["f2"])


async def test_search_and_filters_stay_inside_scope(client, world):
    f2 = world["f2"]
    assert await ids(client, f2, search="carol") == {"2024003"}
    assert await ids(client, f2, search="dave") == set()                             # out of scope even when searched by name
    assert await ids(client, f2, semester=5) == {"2024003"}
    assert await ids(client, f2, subject_id=world["os"]["_id"]) == {"2024003"}
    assert await ids(client, f2, subject_id=world["dbms"]["_id"]) == {"2024001", "2024002"}
    assert await ids(client, f2, department="Information Technology") == set()
    # filtering by someone else's subject is refused rather than silently widened
    r = await client.get("/faculty/me/students", params={"subject_id": world["ds"]["_id"]}, headers=auth(f2))
    assert r.status_code == 403


async def test_list_rows_contain_subjects_and_attendance(client, world):
    await client.post("/attendance/mark", json={"subject_id": world["ds"]["_id"], "date": TODAY, "entries": [
        {"student_id": world["alice_doc"]["_id"], "status": "present"}, {"student_id": world["bob_doc"]["_id"], "status": "absent"}]}, headers=auth(world["f1"]))
    rows = {r["student_id"]: r for r in (await client.get("/faculty/me/students", headers=auth(world["f1"]))).json()}
    assert rows["2024001"]["attendance_percentage"] == 100.0 and rows["2024002"]["attendance_percentage"] == 0.0
    assert [s["name"] for s in rows["2024001"]["subjects"]] == ["Data Structures"]


async def test_detail_scope_and_only_my_subjects_visible(client, world):
    a = world["alice_doc"]["_id"]
    await client.put("/marks", json={"student_id": a, "subject_id": world["dbms"]["_id"], "internal": 77}, headers=auth(world["f2"]))
    d1 = (await client.get(f"/faculty/me/students/{a}", headers=auth(world["f1"]))).json()
    assert [x["subject_name"] for x in d1["academics"]] == ["Data Structures"]        # F1 must NOT see DBMS marks
    assert d1["academics"][0]["marks"] is None
    d2 = (await client.get(f"/faculty/me/students/{a}", headers=auth(world["f2"]))).json()
    assert [x["subject_name"] for x in d2["academics"]] == ["DBMS"] and d2["academics"][0]["marks"]["internal"] == 77
    assert "hashed_password" not in str(d1) and "leave" not in d1

    # out of scope → 403; unknown → 404
    assert (await client.get(f"/faculty/me/students/{world['carol_doc']['_id']}", headers=auth(world["f1"]))).status_code == 403
    assert (await client.get(f"/faculty/me/students/{world['dave_doc']['_id']}", headers=auth(world["f2"]))).status_code == 403
    assert (await client.get("/faculty/me/students/nope", headers=auth(world["f1"]))).status_code == 404


async def test_faculty_without_subjects_sees_nobody(client, world):
    await dbm.faculty_subjects_collection.delete_many({"faculty_id": "1001"})
    assert await ids(client, world["f1"]) == set()
    assert (await client.get(f"/faculty/me/students/{world['alice_doc']['_id']}", headers=auth(world["f1"]))).status_code == 403


async def test_profile_edit_limited_to_phone_and_batch_and_persists_everywhere(client, world):
    a = world["alice_doc"]["_id"]; hf = auth(world["f1"])
    r = await client.put(f"/faculty/me/students/{a}", json={"phone": "9111111111", "batch": "2024-2028"}, headers=hf)
    assert r.status_code == 200, r.text
    # visible in the Admin portal and the faculty detail
    admin_row = next(x for x in (await client.get("/students", headers=auth(world["admin"]))).json() if x["id"] == a)
    assert admin_row["phone"] == "9111111111" and admin_row["batch"] == "2024-2028"
    assert (await client.get(f"/faculty/me/students/{a}", headers=hf)).json()["phone"] == "9111111111"
    # protected fields are refused outright (422), nothing changes
    for forbidden in ({"full_name": "Hacker"}, {"email": "x@gmail.com"}, {"student_id": "1"}, {"department": "Law"}, {"semester": 8}, {"is_active": False}):
        assert (await client.put(f"/faculty/me/students/{a}", json=forbidden, headers=hf)).status_code == 422, forbidden
    assert (await dbm.users_collection.find_one({"_id": world["alice"]["_id"]}))["full_name"] == "Alice Smith"
    assert (await client.put(f"/faculty/me/students/{a}", json={"phone": "12"}, headers=hf)).status_code == 422
    assert (await client.put(f"/faculty/me/students/{a}", json={}, headers=hf)).status_code == 400
    # not my student → 403 and no change
    c = world["carol_doc"]["_id"]
    assert (await client.put(f"/faculty/me/students/{c}", json={"phone": "9222222222"}, headers=hf)).status_code == 403
    assert (await dbm.users_collection.find_one({"_id": world["carol"]["_id"]}))["phone"] == "9876543210"


async def test_faculty_endpoints_closed_to_other_roles(client, world):
    for who in ("admin", "alice"):
        assert (await client.get("/faculty/me/students", headers=auth(world[who]))).status_code == 403
        assert (await client.get(f"/faculty/me/students/{world['alice_doc']['_id']}", headers=auth(world[who]))).status_code == 403
    assert (await client.get("/faculty/me/students")).status_code == 401


# ------------------------------------------------------------ academic operations & ownership

async def test_attendance_ownership_enrolment_and_dates(client, world):
    a, c, d = (world[k]["_id"] for k in ("alice_doc", "carol_doc", "dave_doc"))
    mark = lambda who, subj, entries, day=TODAY: client.post("/attendance/mark", json={"subject_id": subj["_id"], "date": day, "entries": entries}, headers=auth(world[who]))
    ok = [{"student_id": a, "status": "present"}]
    assert (await mark("f1", world["ds"], ok)).status_code == 200
    assert (await mark("f1", world["dbms"], ok)).status_code == 403                  # not my subject
    assert (await mark("f2", world["ds"], ok)).status_code == 403
    assert (await mark("f1", world["ds"], [{"student_id": c, "status": "present"}])).status_code == 403   # carol is sem 5: not enrolled in DS
    assert (await mark("f1", world["ds"], [{"student_id": d, "status": "present"}])).status_code == 403   # dave other department
    assert (await mark("f1", world["ds"], [{"student_id": "ghost", "status": "present"}])).status_code == 404
    assert (await mark("f1", world["ds"], ok, (date.today() + timedelta(days=3)).isoformat())).status_code == 400
    assert (await mark("f1", world["ds"], ok, "garbage")).status_code == 400
    assert (await mark("f1", world["ds"], [])).status_code == 400
    assert (await client.post("/attendance/mark", json={"subject_id": world["ds"]["_id"], "date": TODAY, "entries": [{"student_id": a, "status": "late"}]}, headers=auth(world["f1"]))).status_code == 422
    # a rejected batch must not partially write: only the single valid mark exists
    assert await dbm.attendance_collection.count_documents({}) == 1
    # student can't mark their own attendance
    assert (await mark("alice", world["ds"], ok)).status_code == 403


async def test_attendance_edit_and_view_ownership(client, world):
    a = world["alice_doc"]["_id"]
    await client.post("/attendance/mark", json={"subject_id": world["ds"]["_id"], "date": TODAY, "entries": [{"student_id": a, "status": "present"}]}, headers=auth(world["f1"]))
    rec = (await client.get(f"/attendance/subject/{world['ds']['_id']}", headers=auth(world["f1"]))).json()[0]
    assert (await client.put(f"/attendance/{rec['id']}", json={"status": "absent"}, headers=auth(world["f2"]))).status_code == 403
    assert (await client.get(f"/attendance/subject/{world['ds']['_id']}", headers=auth(world["f2"]))).status_code == 403
    assert (await client.put(f"/attendance/{rec['id']}", json={"status": "absent"}, headers=auth(world["f1"]))).status_code == 200
    assert (await dbm.attendance_collection.find_one({"_id": rec["id"]}))["status"] == "absent"
    # admin is institution-wide
    assert (await client.put(f"/attendance/{rec['id']}", json={"status": "present"}, headers=auth(world["admin"]))).status_code == 200
    assert (await client.get(f"/attendance/subject/{world['ds']['_id']}", headers=auth(world["admin"]))).status_code == 200
    assert (await client.get(f"/attendance/subject/{world['ds']['_id']}", headers=auth(world["alice"]))).status_code == 403


async def test_marks_ownership_validation_and_publish(client, world):
    a, c = world["alice_doc"]["_id"], world["carol_doc"]["_id"]
    put = lambda who, body: client.put("/marks", json=body, headers=auth(world[who]))
    ds = world["ds"]["_id"]
    assert (await put("f1", {"student_id": a, "subject_id": ds, "internal": 30})).status_code == 200
    assert (await put("f1", {"student_id": a, "subject_id": ds, "practical": 25})).status_code == 200    # merges into the same record
    rec = await dbm.marks_collection.find_one({"student_id": a, "subject_id": ds})
    assert (rec["internal"], rec["practical"]) == (30, 25) and await dbm.marks_collection.count_documents({}) == 1
    assert (await put("f2", {"student_id": a, "subject_id": ds, "internal": 1})).status_code == 403       # someone else's subject
    assert (await put("f1", {"student_id": c, "subject_id": ds, "internal": 1})).status_code == 403       # not enrolled
    assert (await put("f1", {"student_id": a, "subject_id": ds, "internal": 101})).status_code == 422
    assert (await put("f1", {"student_id": a, "subject_id": ds, "internal": -1})).status_code == 422
    assert (await put("f1", {"student_id": a, "subject_id": ds})).status_code == 400
    assert (await put("alice", {"student_id": a, "subject_id": ds, "internal": 100})).status_code == 403
    assert (await client.get(f"/marks/subject/{ds}", headers=auth(world["f2"]))).status_code == 403
    assert len((await client.get(f"/marks/subject/{ds}", headers=auth(world["f1"]))).json()) == 1
    # another faculty can't publish my marks; I can; admin can too
    assert (await client.put(f"/marks/{rec['_id']}/publish", headers=auth(world["f2"]))).status_code == 403
    assert (await dbm.marks_collection.find_one({"_id": rec["_id"]}))["published"] is False
    assert (await client.put(f"/marks/{rec['_id']}/publish", headers=auth(world["f1"]))).status_code == 200
    # admin may correct marks anywhere
    assert (await put("admin", {"student_id": a, "subject_id": ds, "internal": 35})).status_code == 200
    assert (await client.get("/marks/mine", headers=auth(world["alice"]))).json()[0]["internal"] == 35
    # another student never sees it
    assert (await client.get("/marks/mine", headers=auth(world["bob"]))).json() == []


async def test_assignment_submission_and_grading_ownership(client, world):
    due = (date.today() + timedelta(days=5)).isoformat()
    r = await client.post("/assignments", json={"title": "Trees", "description": "d", "subject_id": world["ds"]["_id"], "due_date": due}, headers=auth(world["f1"]))
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    assert (await client.post("/assignments", json={"title": "x", "description": "d", "subject_id": world["ds"]["_id"], "due_date": due}, headers=auth(world["f2"]))).status_code == 403

    # alice (enrolled) submits; carol (sem 5) cannot submit to a sem-3 assignment
    assert (await client.post(f"/assignments/{aid}/submit", json={"file_url": "/uploads/x.pdf"}, headers=auth(world["alice"]))).status_code == 200
    assert (await client.post(f"/assignments/{aid}/submit", json={"file_url": "/uploads/x.pdf"}, headers=auth(world["carol"]))).status_code == 403
    assert (await client.post(f"/assignments/{aid}/submit", json={"file_url": "/uploads/x.pdf"}, headers=auth(world["f1"]))).status_code == 403

    subs_r = await client.get(f"/assignments/{aid}/submissions", headers=auth(world["f1"]))
    assert subs_r.status_code == 200 and len(subs_r.json()) == 1
    sub_id = subs_r.json()[0]["id"]
    assert (await client.get(f"/assignments/{aid}/submissions", headers=auth(world["f2"]))).status_code == 403
    assert (await client.put(f"/assignments/submissions/{sub_id}/grade", json={"grade": "A"}, headers=auth(world["f2"]))).status_code == 403
    assert (await client.put(f"/assignments/submissions/{sub_id}/grade", json={"grade": ""}, headers=auth(world["f1"]))).status_code == 422
    assert (await client.put(f"/assignments/submissions/{sub_id}/grade", json={"grade": "A", "feedback": "Great"}, headers=auth(world["f1"]))).status_code == 200

    # grade appears in the student's portal and in both faculty/admin student views
    mine = (await client.get("/assignments/mine", headers=auth(world["alice"]))).json()
    assert mine[0]["grade"] == "A" and mine[0]["submission_status"] == "graded"
    fd = (await client.get(f"/faculty/me/students/{world['alice_doc']['_id']}", headers=auth(world["f1"]))).json()
    asg = fd["academics"][0]["assignments"][0]
    assert (asg["grade"], asg["status"], asg["submission_id"]) == ("A", "graded", sub_id)
    ad = (await client.get(f"/students/{world['alice_doc']['_id']}", headers=auth(world["admin"]))).json()
    ds_row = next(x for x in ad["academics"] if x["subject_name"] == "Data Structures")
    assert ds_row["assignments"][0]["grade"] == "A"
    # subject assignment listing is scoped too
    assert (await client.get(f"/assignments/subject/{world['ds']['_id']}", headers=auth(world["f2"]))).status_code == 403
    assert (await client.get(f"/assignments/subject/{world['ds']['_id']}", headers=auth(world["carol"]))).status_code == 403
    assert (await client.get(f"/assignments/subject/{world['ds']['_id']}", headers=auth(world["bob"]))).status_code == 200


async def test_roster_scoped_for_faculty_open_for_admin(client, world):
    assert len((await client.get("/students/roster", params={"subject_id": world["ds"]["_id"]}, headers=auth(world["f1"]))).json()) == 2
    assert (await client.get("/students/roster", params={"subject_id": world["ds"]["_id"]}, headers=auth(world["f2"]))).status_code == 403
    assert (await client.get("/students/roster", params={"subject_id": world["ds"]["_id"]}, headers=auth(world["admin"]))).status_code == 200
    assert (await client.get("/students/roster", params={"subject_id": world["ds"]["_id"]}, headers=auth(world["alice"]))).status_code == 403
    assert (await client.get("/students/roster", params={"subject_id": "nope"}, headers=auth(world["admin"]))).status_code == 404


async def test_jwt_edge_cases(client, world):
    from app.auth import create_access_token, create_refresh_token
    assert (await client.get("/students", headers={"Authorization": "Bearer garbage"})).status_code == 401
    refresh, _, _ = create_refresh_token({"sub": world["admin"]["_id"]})
    assert (await client.get("/students", headers={"Authorization": f"Bearer {refresh}"})).status_code == 401   # refresh token isn't an access token
    # a forged role claim is ignored: the role comes from the database, not the token
    forged = create_access_token({"sub": world["alice"]["_id"], "role": "admin"})
    assert (await client.get("/students", headers={"Authorization": f"Bearer {forged}"})).status_code == 403
    expired = create_access_token({"sub": world["admin"]["_id"], "role": "admin"}, expires_minutes=-5)
    assert (await client.get("/students", headers={"Authorization": f"Bearer {expired}"})).status_code == 401
    ghost = create_access_token({"sub": "no-such-user", "role": "admin"})
    assert (await client.get("/students", headers={"Authorization": f"Bearer {ghost}"})).status_code == 401
