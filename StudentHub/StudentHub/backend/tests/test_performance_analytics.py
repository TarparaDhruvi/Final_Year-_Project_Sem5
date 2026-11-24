"""Part 1: Student Performance Analytics. Expected numbers below were worked out by hand."""
import math
from datetime import datetime, timedelta, timezone

import pytest

from conftest import auth
from app import database as dbm
from app.services.performance_analytics import compute_performance, record_percentage, grade_for

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def students(*ids, dept="D", sem=1):
    return [{"_id": i, "department": dept, "semester": sem} for i in ids]


def subjects(*ids, dept="D", sem=1):
    return [{"_id": i, "name": f"Subject {i}", "code": i.upper(), "department": dept, "semester": sem} for i in ids]


def mk(student, subject, internal=None, practical=None, published=True, minutes=0, **extra):
    return {"_id": f"{student}-{subject}-{minutes}", "student_id": student, "subject_id": subject, "internal": internal,
            "practical": practical, "published": published, "updated_at": T0 + timedelta(minutes=minutes), **extra}


def test_hand_computed_scenario():
    st = students("a", "b", "c", "d", "e")
    sj = subjects("s1", "s2")
    marks = [
        mk("a", "s1", 90, 90), mk("a", "s2", 80),            # 90 and 80  -> 85   (A, pass)
        mk("b", "s1", 30, 30), mk("b", "s2", 50),            # 30 and 50  -> 40   (E, pass: 40 >= 40)
        mk("c", "s1", 20),                                   # 20; s2 missing -> 1/2 coverage is enough -> 20 (F, fail)
        # d: no marks at all -> insufficient, NOT a failure
        mk("e", "s1", -5, "abc"),                            # only invalid values -> insufficient
    ]
    r = compute_performance(st, sj, marks, pass_pct=40)
    s = r["summary"]
    assert (s["students_total"], s["students_eligible"], s["students_insufficient_data"]) == (5, 3, 2)
    assert s["average_percentage"] == 48.3                    # (85 + 40 + 20) / 3
    assert (s["pass_count"], s["fail_count"], s["pass_rate"], s["fail_rate"]) == (2, 1, 66.7, 33.3)
    dist = {d["grade"]: d for d in r["grade_distribution"]}
    assert {g: dist[g]["count"] for g in dist} == {"A+": 0, "A": 1, "B": 0, "C": 0, "D": 0, "E": 1, "F": 1}
    assert dist["A"]["percentage"] == 33.3 and sum(d["count"] for d in dist.values()) == s["students_eligible"] == s["pass_count"] + s["fail_count"]
    assert r["data_quality"]["invalid_ignored"] == 1
    # subject averages: s1 = (90+30+20)/3, s2 = (80+50)/2
    by = {x["subject_id"]: x for x in r["by_subject"]}
    assert by["s1"]["average_percentage"] == 46.7 and by["s1"]["students_count"] == 3
    assert by["s2"]["average_percentage"] == 65.0 and by["s2"]["students_count"] == 2


def test_different_maximum_marks_are_normalised():
    st, sj = students("f"), subjects("s1", "s2")
    marks = [mk("f", "s1", 45, 40, max_internal=50, max_practical=50),   # (45+40)/(50+50) = 85%
             mk("f", "s2", 18, max_internal=20)]                          # 18/20 = 90%
    r = compute_performance(st, sj, marks, pass_pct=40)
    assert r["summary"]["average_percentage"] == 87.5                     # (85 + 90) / 2
    assert record_percentage({"internal": 18, "max_internal": 20}) == (90.0, False)
    # unequal maximums inside one record are weighted by maximum: (10+40)/(10+90)=50%, not the average of 100% and 44.4%
    assert record_percentage({"internal": 10, "max_internal": 10, "practical": 40, "max_practical": 90})[0] == pytest.approx(50.0)


@pytest.mark.parametrize("doc,expected_valid", [
    ({"internal": 50, "max_internal": 0}, False),          # invalid maximum
    ({"internal": 50, "max_internal": -10}, False),
    ({"internal": 50, "max_internal": "x"}, False),
    ({"internal": 120}, False),                            # above the default maximum of 100
    ({"internal": -1}, False),
    ({"internal": float("nan")}, False),
    ({"internal": float("inf")}, False),
    ({"internal": True}, False),                           # booleans are not marks
    ({"internal": "80"}, False),                           # strings are not marks
    ({"internal": None, "practical": None}, False),        # nothing entered
    ({"internal": 0}, True),                               # a real zero IS a valid mark
    ({"internal": 100}, True),
    ({"internal": None, "practical": 70}, True),
])
def test_invalid_values_are_ignored_safely(doc, expected_valid):
    pct, _ = record_percentage(doc)
    assert (pct is not None) is expected_valid
    r = compute_performance(students("a"), subjects("s1"), [{"_id": "x", "student_id": "a", "subject_id": "s1", **doc}])
    assert r["summary"]["students_eligible"] == (1 if expected_valid else 0)
    assert r["summary"]["students_insufficient_data"] == (0 if expected_valid else 1)   # never silently a "fail"
    assert r["summary"]["fail_count"] == 0 or expected_valid


def test_one_bad_component_does_not_discard_the_good_one():
    pct, invalid = record_percentage({"internal": 150, "practical": 60})
    assert pct == 60.0 and invalid is True


def test_duplicates_use_latest_valid_record_and_are_counted():
    st, sj = students("g"), subjects("s1")
    r = compute_performance(st, sj, [mk("g", "s1", 10, minutes=1), mk("g", "s1", 70, minutes=5)])
    assert r["summary"]["average_percentage"] == 70.0 and r["data_quality"]["duplicates_ignored"] == 1
    # newest record is invalid -> fall back to the older valid one
    r = compute_performance(st, sj, [mk("g", "s1", 40, minutes=1), mk("g", "s1", 999, minutes=9)])
    assert r["summary"]["average_percentage"] == 40.0
    # the duplicate does not double-count the student or the subject average
    r = compute_performance(st, sj, [mk("g", "s1", 50, minutes=1), mk("g", "s1", 50, minutes=2), mk("g", "s1", 50, minutes=3)])
    assert r["summary"]["students_eligible"] == 1 and r["by_subject"][0]["students_count"] == 1 and r["data_quality"]["duplicates_ignored"] == 2


def test_coverage_rule_needs_half_of_the_class_subjects():
    st, sj = students("a", "b"), subjects("s1", "s2", "s3", "s4")
    marks = [mk("a", "s1", 90), mk("b", "s1", 90), mk("b", "s2", 70)]
    r = compute_performance(st, sj, marks)
    assert r["summary"]["students_eligible"] == 1 and r["summary"]["students_insufficient_data"] == 1     # a: 1/4, b: 2/4
    assert r["summary"]["average_percentage"] == 80.0                                                       # b only: (90+70)/2


def test_marks_for_other_classes_and_unknown_students_are_ignored():
    st, sj = students("a"), subjects("s1") + subjects("other", dept="X", sem=9)
    marks = [mk("a", "s1", 60), mk("a", "other", 5), mk("ghost", "s1", 99)]
    r = compute_performance(st, sj, marks)
    assert r["summary"]["average_percentage"] == 60.0 and r["data_quality"]["outside_class_ignored"] == 2


def test_published_only_filter():
    st, sj = students("a", "b"), subjects("s1")
    marks = [mk("a", "s1", 80, published=True), mk("b", "s1", 20, published=False)]
    assert compute_performance(st, sj, marks)["summary"]["students_eligible"] == 2
    r = compute_performance(st, sj, marks, published_only=True)
    assert r["summary"]["students_eligible"] == 1 and r["summary"]["average_percentage"] == 80.0 and r["data_quality"]["unpublished_ignored"] == 1
    assert compute_performance(st, sj, marks)["data_quality"]["unpublished_included"] == 1


def test_empty_database_and_no_marks_give_empty_not_failures():
    r = compute_performance([], [], [])
    assert r["summary"]["students_total"] == 0 and r["summary"]["average_percentage"] is None and r["summary"]["pass_rate"] is None
    assert all(d["count"] == 0 and d["percentage"] == 0.0 for d in r["grade_distribution"]) and r["by_subject"] == []
    r = compute_performance(students("a", "b"), subjects("s1"), [])
    assert r["summary"]["fail_count"] == 0 and r["summary"]["students_insufficient_data"] == 2     # not failures
    r = compute_performance(students("a"), [], [])                                                   # a class with no subjects
    assert r["summary"]["students_insufficient_data"] == 1


def test_pass_threshold_is_configurable(monkeypatch):
    st, sj = students("a", "b"), subjects("s1")
    marks = [mk("a", "s1", 45), mk("b", "s1", 55)]
    assert compute_performance(st, sj, marks)["summary"]["pass_count"] == 2                     # default 40
    monkeypatch.setenv("PASS_PERCENTAGE", "50")
    r = compute_performance(st, sj, marks)
    assert (r["summary"]["pass_count"], r["summary"]["fail_count"], r["config"]["pass_percentage"]) == (1, 1, 50.0)
    monkeypatch.setenv("PASS_PERCENTAGE", "not-a-number")
    assert compute_performance(st, sj, marks)["config"]["pass_percentage"] == 40.0
    monkeypatch.setenv("PASS_PERCENTAGE", "150")
    assert compute_performance(st, sj, marks)["config"]["pass_percentage"] == 40.0


@pytest.mark.parametrize("pct,grade", [(100, "A+"), (90, "A+"), (89.99, "A"), (80, "A"), (70, "B"), (60, "C"), (50, "D"), (40, "E"), (39.99, "F"), (0, "F")])
def test_grade_boundaries(pct, grade):
    assert grade_for(pct) == grade


def test_percentages_and_counts_are_internally_consistent():
    import random
    rnd = random.Random(7)
    ids = [f"s{i}" for i in range(60)]
    st, sj = students(*ids), subjects("a", "b", "c")
    marks = [mk(i, s, rnd.randint(0, 100), rnd.choice([None, rnd.randint(0, 100)])) for i in ids for s in ("a", "b", "c") if rnd.random() < 0.8]
    r = compute_performance(st, sj, marks)
    s = r["summary"]
    assert s["students_eligible"] + s["students_insufficient_data"] == s["students_total"] == 60
    assert s["pass_count"] + s["fail_count"] == s["students_eligible"] == sum(d["count"] for d in r["grade_distribution"])
    assert sum(d["percentage"] for d in r["grade_distribution"]) == pytest.approx(100, abs=0.5)
    assert 0 <= s["average_percentage"] <= 100


# ------------------------------------------------------------ endpoint

async def put_marks(client, world, who, student, subject, internal=None, practical=None):
    body = {"student_id": world[student]["_id"], "subject_id": world[subject]["_id"]}
    if internal is not None: body["internal"] = internal
    if practical is not None: body["practical"] = practical
    r = await client.put("/marks", json=body, headers=auth(world[who]))
    assert r.status_code == 200, r.text


async def perf(client, world, **params):
    r = await client.get("/analytics/student-performance", params=params, headers=auth(world["admin"]))
    assert r.status_code == 200, r.text
    return r.json()


async def test_endpoint_empty_database_state(client, world):
    r = await perf(client, world)
    assert r["summary"]["students_eligible"] == 0 and r["summary"]["average_percentage"] is None and r["summary"]["fail_count"] == 0
    assert r["summary"]["students_total"] == 4 and r["summary"]["students_insufficient_data"] == 4


async def test_endpoint_uses_real_marks_and_updates_when_marks_change(client, world):
    # alice (CS sem3): DS 80, DBMS 60 -> 70.  bob (CS sem3): DS 30 only (1 of 2 subjects is enough) -> 30.
    await put_marks(client, world, "f1", "alice_doc", "ds", 80, 80)
    await put_marks(client, world, "f2", "alice_doc", "dbms", 60)
    await put_marks(client, world, "f1", "bob_doc", "ds", 30, 30)
    r = await perf(client, world)
    s = r["summary"]
    assert (s["students_eligible"], s["average_percentage"], s["pass_count"], s["fail_count"]) == (2, 50.0, 1, 1)
    dist = {d["grade"]: d["count"] for d in r["grade_distribution"]}
    assert dist["B"] == 1 and dist["F"] == 1 and sum(dist.values()) == 2

    # marks change -> the very next call reflects it (nothing cached): bob 30 -> 90
    await put_marks(client, world, "f1", "bob_doc", "ds", 90, 90)
    s = (await perf(client, world))["summary"]
    assert (s["average_percentage"], s["pass_count"], s["fail_count"]) == (80.0, 2, 0)

    # filters: one subject, one department/semester
    only_ds = await perf(client, world, subject_id=world["ds"]["_id"])
    assert only_ds["summary"]["students_total"] == 2 and only_ds["summary"]["average_percentage"] == 85.0     # alice 80, bob 90
    assert [x["name"] for x in only_ds["by_subject"]] == ["Data Structures"]
    sem5 = await perf(client, world, department="Computer Science", semester=5)
    assert sem5["summary"]["students_total"] == 1 and sem5["summary"]["students_eligible"] == 0           # carol: no marks yet
    it = await perf(client, world, department="Information Technology")
    assert it["summary"]["students_total"] == 1 and it["summary"]["fail_count"] == 0                        # dave: no subjects mapped -> not a failure
    assert (await perf(client, world, subject_id="no-such-subject"))["summary"]["students_total"] == 0

    # drafts vs published
    assert (await perf(client, world, published_only=True))["summary"]["students_eligible"] == 0
    rec = await dbm.marks_collection.find_one({"student_id": world["alice_doc"]["_id"], "subject_id": world["ds"]["_id"]})
    await client.put(f"/marks/{rec['_id']}/publish", headers=auth(world["f1"]))
    assert (await perf(client, world, published_only=True))["summary"]["students_eligible"] == 1


async def test_endpoint_handles_duplicate_and_garbage_documents(client, world):
    a, ds = world["alice_doc"]["_id"], world["ds"]["_id"]
    now = datetime.now(timezone.utc)
    await dbm.marks_collection.insert_many([
        {"_id": "m1", "student_id": a, "subject_id": ds, "internal": 20, "practical": None, "published": True, "updated_at": now - timedelta(days=2)},
        {"_id": "m2", "student_id": a, "subject_id": ds, "internal": 70, "practical": 70, "published": True, "updated_at": now},
        {"_id": "m3", "student_id": world["bob_doc"]["_id"], "subject_id": ds, "internal": "garbage", "practical": float("nan"), "published": True},
        {"_id": "m4", "student_id": "deleted-student", "subject_id": ds, "internal": 99, "published": True},
    ])
    r = await perf(client, world)
    assert r["summary"]["students_eligible"] == 1 and r["summary"]["average_percentage"] == 70.0
    assert r["data_quality"]["duplicates_ignored"] == 1 and r["data_quality"]["invalid_ignored"] == 1
    assert r["data_quality"]["records_total"] == 3        # the orphaned mark of a deleted student is filtered out by the query itself
    assert r["summary"]["fail_count"] == 0                                                                  # bob's garbage is not a failure


async def test_endpoint_is_admin_only_and_exposes_no_student_data(client, world):
    await put_marks(client, world, "f1", "alice_doc", "ds", 77)
    for who in ("f1", "alice"):
        assert (await client.get("/analytics/student-performance", headers=auth(world[who]))).status_code == 403
    assert (await client.get("/analytics/student-performance")).status_code == 401
    assert (await client.get("/analytics/student-performance", headers={"Authorization": "Bearer junk"})).status_code == 401
    body = (await client.get("/analytics/student-performance", headers=auth(world["admin"]))).text
    for secret in ("Alice", "alice@gmail.com", "2024001", world["alice_doc"]["_id"], world["alice"]["_id"], "hashed_password", "Faculty One"):
        assert secret not in body, secret
    assert "workload" not in body.lower()


async def test_other_dashboard_data_still_available_to_admin(client, world):
    for path in ("/students", "/faculty", "/subjects", "/leave", "/analytics/faculty-heatmap", "/analytics/campus-pulse"):
        assert (await client.get(path, headers=auth(world["admin"]))).status_code == 200, path
