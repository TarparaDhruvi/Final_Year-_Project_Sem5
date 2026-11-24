"""Priority 4: Admin student management — CRUD, search/filter, duplicates, validation, status, profile records."""
from datetime import date

import pytest

from conftest import auth, PASSWORD
from app import database as dbm

NEW = {"full_name": "Eve Adams", "email": "eve@gmail.com", "password": "Strong@123", "phone": "9123456780",
       "student_id": "2024099", "department": "Computer Science", "semester": 3, "batch": "2024-2028"}


async def test_only_admin_can_use_student_admin_endpoints(client, world):
    sid = world["alice_doc"]["_id"]
    calls = [("GET", "/students", None), ("POST", "/students", NEW), ("GET", f"/students/{sid}", None),
             ("PUT", f"/students/{sid}", {"phone": "9999999999"}), ("PATCH", f"/students/{sid}/status", {"is_active": False}),
             ("DELETE", f"/students/{sid}", None), ("POST", f"/students/{sid}/reset-password", None)]
    for who in ("f1", "alice"):
        for m, p, b in calls:
            r = await client.request(m, p, json=b, headers=auth(world[who]))
            assert r.status_code == 403, f"{who} {m} {p} -> {r.status_code}"
    for m, p, b in calls:
        assert (await client.request(m, p, json=b)).status_code == 401
    assert await dbm.users_collection.find_one({"email": "eve@gmail.com"}) is None


async def test_create_persists_and_new_student_can_log_in(client, world):
    h = auth(world["admin"])
    r = await client.post("/students", json=NEW, headers=h)
    assert r.status_code == 201, r.text
    assert await dbm.students_collection.find_one({"student_id": "2024099"})
    login = await client.post("/auth/login/student", json={"email": "eve@gmail.com", "password": "Strong@123"})
    assert login.status_code == 200 and login.json()["user"]["role"] == "student"


async def test_duplicates_rejected(client, world):
    h = auth(world["admin"])
    assert (await client.post("/students", json=NEW, headers=h)).status_code == 201
    r = await client.post("/students", json={**NEW, "student_id": "2024100"}, headers=h)
    assert r.status_code == 409 and "email" in r.json()["detail"].lower()
    r = await client.post("/students", json={**NEW, "email": "other@gmail.com"}, headers=h)
    assert r.status_code == 409 and "student id" in r.json()["detail"].lower()
    # case-insensitive email duplicate
    r = await client.post("/students", json={**NEW, "email": "EVE@gmail.com", "student_id": "2024101"}, headers=h)
    assert r.status_code == 409
    assert await dbm.students_collection.count_documents({"student_id": {"$in": ["2024099", "2024100", "2024101"]}}) == 1
    # a faculty member's ID can't be reused as a student ID either
    r = await client.post("/students", json={**NEW, "email": "z@gmail.com", "student_id": "1001"}, headers=h)
    assert r.status_code == 409


@pytest.mark.parametrize("field,value", [
    ("full_name", "X1"), ("full_name", "Ab"), ("email", "eve@yahoo.com"), ("email", "not-an-email"), ("password", "weak"),
    ("phone", "123"), ("phone", "abcdefghij"), ("student_id", "ABC123"), ("semester", 0), ("semester", 9), ("department", "   "),
])
async def test_create_validation(client, world, field, value):
    r = await client.post("/students", json={**NEW, field: value}, headers=auth(world["admin"]))
    assert r.status_code == 422, f"{field}={value!r} -> {r.status_code}"
    assert await dbm.students_collection.find_one({"student_id": "2024099"}) is None


async def test_list_search_filter(client, world):
    h = auth(world["admin"])
    all_rows = (await client.get("/students", headers=h)).json()
    assert [r["student_id"] for r in all_rows] == ["2024001", "2024002", "2024003", "2024004"]
    q = lambda **p: client.get("/students", params=p, headers=h)
    assert [r["full_name"] for r in (await q(search="alice")).json()] == ["Alice Smith"]
    assert [r["student_id"] for r in (await q(search="2024003")).json()] == ["2024003"]
    assert [r["student_id"] for r in (await q(search="BOB@GMAIL")).json()] == ["2024002"]
    assert [r["student_id"] for r in (await q(search="9876543210")).json()] == ["2024001", "2024002", "2024003", "2024004"]
    assert {r["student_id"] for r in (await q(department="Computer Science")).json()} == {"2024001", "2024002", "2024003"}
    assert {r["student_id"] for r in (await q(semester=3)).json()} == {"2024001", "2024002", "2024004"}
    assert {r["student_id"] for r in (await q(department="Computer Science", semester=3)).json()} == {"2024001", "2024002"}
    assert (await q(search="nobody-here")).json() == []
    assert (await q(status="weird")).status_code == 400


async def test_edit_persists_and_validates_and_blocks_duplicates(client, world):
    h = auth(world["admin"]); sid = world["alice_doc"]["_id"]
    r = await client.put(f"/students/{sid}", json={"full_name": "Alice Jones", "phone": "9000000001", "department": "Information Technology",
                                                   "semester": 4, "batch": "2023-2027", "email": "alice.j@gmail.com", "student_id": "2024555"}, headers=h)
    assert r.status_code == 200, r.text
    row = next(x for x in (await client.get("/students", headers=h)).json() if x["id"] == sid)
    assert (row["full_name"], row["phone"], row["department"], row["semester"], row["batch"], row["email"], row["student_id"]) == \
        ("Alice Jones", "9000000001", "Information Technology", 4, "2023-2027", "alice.j@gmail.com", "2024555")
    # login identity moved with the edit
    assert (await client.post("/auth/login/student", json={"email": "alice.j@gmail.com", "password": PASSWORD})).status_code == 200
    assert (await client.post("/auth/login/student", json={"email": "alice@gmail.com", "password": PASSWORD})).status_code == 401
    assert (await dbm.users_collection.find_one({"_id": world["alice"]["_id"]}))["login_id"] == "2024555"

    # duplicates against someone else
    assert (await client.put(f"/students/{sid}", json={"email": "bob@gmail.com"}, headers=h)).status_code == 409
    assert (await client.put(f"/students/{sid}", json={"student_id": "2024002"}, headers=h)).status_code == 409
    # re-saving your own email / id is fine
    assert (await client.put(f"/students/{sid}", json={"email": "alice.j@gmail.com", "student_id": "2024555"}, headers=h)).status_code == 200
    # validation
    for bad in ({"full_name": "X"}, {"phone": "12"}, {"semester": 12}, {"email": "a@yahoo.com"}, {"student_id": "abc"}, {"department": ""}):
        assert (await client.put(f"/students/{sid}", json=bad, headers=h)).status_code == 422, bad
    # clear batch
    await client.put(f"/students/{sid}", json={"batch": ""}, headers=h)
    assert (await dbm.students_collection.find_one({"_id": sid}))["batch"] is None
    assert (await client.put("/students/does-not-exist", json={"phone": "9000000001"}, headers=h)).status_code == 404


async def test_deactivate_blocks_login_and_existing_tokens_then_reactivate(client, world):
    h = auth(world["admin"]); sid = world["alice_doc"]["_id"]
    login = (await client.post("/auth/login/student", json={"email": "alice@gmail.com", "password": PASSWORD})).json()
    ha = {"Authorization": f"Bearer {login['access_token']}"}
    assert (await client.get("/auth/me", headers=ha)).status_code == 200

    assert (await client.patch(f"/students/{sid}/status", json={"is_active": False}, headers=h)).status_code == 200
    assert (await client.post("/auth/login/student", json={"email": "alice@gmail.com", "password": PASSWORD})).status_code == 403
    assert (await client.get("/auth/me", headers=ha)).status_code == 403                       # live token stops working
    assert (await client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})).status_code in (401, 403)
    assert (await client.get("/students", params={"status": "inactive"}, headers=h)).json()[0]["student_id"] == "2024001"
    assert "2024001" not in [r["student_id"] for r in (await client.get("/students", params={"status": "active"}, headers=h)).json()]
    # records preserved
    assert await dbm.students_collection.find_one({"_id": sid})

    assert (await client.patch(f"/students/{sid}/status", json={"is_active": True}, headers=h)).status_code == 200
    assert (await client.post("/auth/login/student", json={"email": "alice@gmail.com", "password": PASSWORD})).status_code == 200


async def test_profile_shows_academic_records_from_other_portals(client, world):
    """Faculty records attendance/marks/grades → Admin profile and the Student's own portal both show them."""
    today = date.today().isoformat()
    a_id = world["alice_doc"]["_id"]; ds = world["ds"]["_id"]
    hf1 = auth(world["f1"])
    assert (await client.post("/attendance/mark", json={"subject_id": ds, "date": today, "entries": [{"student_id": a_id, "status": "present"}, {"student_id": world["bob_doc"]["_id"], "status": "absent"}]}, headers=hf1)).status_code == 200
    assert (await client.put("/marks", json={"student_id": a_id, "subject_id": ds, "internal": 42, "practical": 38}, headers=hf1)).status_code == 200

    prof = (await client.get(f"/students/{a_id}", headers=auth(world["admin"]))).json()
    assert prof["full_name"] == "Alice Smith" and prof["email"] == "alice@gmail.com" and prof["is_active"] is True
    by_name = {a["subject_name"]: a for a in prof["academics"]}
    assert set(by_name) == {"Data Structures", "DBMS"}                       # only the student's own class subjects
    assert by_name["Data Structures"]["attendance"] == {"present": 1, "total": 1, "percentage": 100.0, "at_risk": False}
    assert by_name["Data Structures"]["marks"]["internal"] == 42 and by_name["Data Structures"]["marks"]["published"] is False
    assert by_name["Data Structures"]["faculty_name"] == "Faculty One"
    assert by_name["DBMS"]["attendance"]["percentage"] is None

    # unpublished marks are invisible to the student; after publish they appear
    hs = auth(world["alice"])
    assert (await client.get("/marks/mine", headers=hs)).json() == []
    mid = by_name["Data Structures"]["marks"]["id"]
    assert (await client.put(f"/marks/{mid}/publish", headers=hf1)).status_code == 200
    mine = (await client.get("/marks/mine", headers=hs)).json()
    assert mine[0]["internal"] == 42 and mine[0]["subject_name"] == "Data Structures"
    att = (await client.get("/attendance/me", headers=hs)).json()
    assert att[0]["percentage"] == 100.0


async def test_delete_student(client, world):
    h = auth(world["admin"]); sid = world["dave_doc"]["_id"]
    assert (await client.delete(f"/students/{sid}", headers=h)).status_code == 200
    assert await dbm.users_collection.find_one({"email": "dave@gmail.com"}) is None
    assert (await client.delete(f"/students/{sid}", headers=h)).status_code == 404


async def test_reset_password_gives_working_temp_password(client, world):
    r = await client.post(f"/students/{world['alice_doc']['_id']}/reset-password", headers=auth(world["admin"]))
    pw = r.json()["temporary_password"]
    from app.utils.validators import validate_password
    assert validate_password(pw) is None
    assert (await client.post("/auth/login/student", json={"email": "alice@gmail.com", "password": pw})).status_code == 200
    assert (await client.post("/auth/login/student", json={"email": "alice@gmail.com", "password": PASSWORD})).status_code == 401
