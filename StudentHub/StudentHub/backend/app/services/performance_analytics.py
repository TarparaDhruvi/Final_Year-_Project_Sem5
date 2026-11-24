"""
services/performance_analytics.py — Student Performance Analytics (Admin dashboard)

Pure functions (no database access) so every rule below can be unit-tested. All numbers come from the
`marks`, `students` and `subjects` collections; nothing is hardcoded or cached.

WHAT THE DATA CONTAINS
  One `marks` document per (student, subject) with `internal` and `practical` scores. The API only accepts
  0–100 for each, and no maximum is stored, so a component's maximum DEFAULTS TO 100. If a document does carry
  `max_internal` / `max_practical`, those are honoured, so assessments with different maximums normalise correctly.

METHOD (documented so the numbers can be audited)
  1. Component validity. A score counts only if it is a finite number >= 0, its maximum is a finite number > 0
     (a max field that is present but invalid makes that component invalid), and score <= maximum.
     Missing (null) scores are "not yet entered", not zero. A record with no valid component is ignored.
  2. Record percentage = (sum of valid scores) / (sum of their maximums) x 100. (With the default 100/100
     maximums this is the plain average of internal and practical.)
  3. Duplicates. If a student has several documents for the same subject, only the most recently updated VALID one
     is used; the rest are counted in `data_quality.duplicates_ignored`.
  4. Student result = the mean of that student's subject percentages (each subject weighs equally), counting only
     subjects of the student's own class (same department + semester).
  5. Eligibility. A student is ELIGIBLE only with valid results in at least MIN_COVERAGE (50%) of their class's
     subjects (at least one). Everyone else is "insufficient data" — they are never counted as failures and are
     excluded from the average, grade distribution and pass/fail denominator, so all three always use the same students.
  6. Pass / fail. Pass if the student result >= PASS_PERCENTAGE (env, default 40 — a PROVISIONAL default because the
     project has no institutional rule). Select one subject to see pass/fail for that subject alone.
  7. Grades (no institutional scale exists, so fixed percentage bands, independent of the pass mark):
     A+ >=90 · A >=80 · B >=70 · C >=60 · D >=50 · E >=40 · F <40.

Only aggregates are returned — never names, IDs or any per-student values.
"""
import math
import os
from datetime import datetime, timezone

GRADE_BANDS = [("A+", 90, "Outstanding"), ("A", 80, "Excellent"), ("B", 70, "Very good"),
               ("C", 60, "Good"), ("D", 50, "Satisfactory"), ("E", 40, "Pass"), ("F", 0, "Below 40%")]
MIN_COVERAGE = 0.5
DEFAULT_PASS_PERCENTAGE = 40.0


def pass_percentage() -> float:
    try:
        v = float(os.getenv("PASS_PERCENTAGE", str(DEFAULT_PASS_PERCENTAGE)))
        return v if 0 <= v <= 100 and math.isfinite(v) else DEFAULT_PASS_PERCENTAGE
    except ValueError:
        return DEFAULT_PASS_PERCENTAGE


def _num(v):
    """A real, finite number — booleans, strings, NaN and infinity are rejected."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if math.isfinite(v) else None


def _component(doc: dict, score_key: str, max_key: str):
    """(obtained, maximum) for a valid component, None if not entered, False if present but invalid."""
    raw = doc.get(score_key)
    if raw is None:
        return None
    score = _num(raw)
    if max_key in doc and doc[max_key] is not None:
        maximum = _num(doc[max_key])
    else:
        maximum = 100.0
    if score is None or maximum is None or maximum <= 0 or score < 0 or score > maximum:
        return False
    return score, maximum


def record_percentage(doc: dict):
    """Returns (percentage | None, had_invalid_component)."""
    got, total, invalid = 0.0, 0.0, False
    for score_key, max_key in (("internal", "max_internal"), ("practical", "max_practical")):
        c = _component(doc, score_key, max_key)
        if c is False:
            invalid = True
        elif c is not None:
            got += c[0]
            total += c[1]
    if total <= 0:
        return None, invalid
    return got / total * 100.0, invalid


def _ts(doc: dict) -> float:
    for key in ("updated_at", "created_at"):
        v = doc.get(key)
        if isinstance(v, datetime):
            return (v if v.tzinfo else v.replace(tzinfo=timezone.utc)).timestamp()
    return 0.0


def grade_for(pct: float) -> str:
    for grade, floor, _ in GRADE_BANDS:
        if pct >= floor:
            return grade
    return "F"


def compute_performance(students: list[dict], subjects: list[dict], marks: list[dict], *, published_only: bool = False,
                        pass_pct: float | None = None, min_coverage: float = MIN_COVERAGE) -> dict:
    pass_pct = pass_percentage() if pass_pct is None else pass_pct
    subjects_by_id = {s["_id"]: s for s in subjects}
    class_subjects: dict = {}
    for s in subjects:
        class_subjects.setdefault((s.get("department"), s.get("semester")), set()).add(s["_id"])
    students_by_id = {s["_id"]: s for s in students}

    quality = {"records_total": len(marks), "records_used": 0, "duplicates_ignored": 0, "invalid_ignored": 0,
               "outside_class_ignored": 0, "unpublished_ignored": 0, "unpublished_included": 0}

    # ---- group candidate records per (student, subject) and pick one valid, most recent record
    groups: dict = {}
    for m in marks:
        sid, subj = m.get("student_id"), m.get("subject_id")
        student = students_by_id.get(sid)
        if student is None or subj not in subjects_by_id or subj not in class_subjects.get((student.get("department"), student.get("semester")), set()):
            quality["outside_class_ignored"] += 1
            continue
        if published_only and not m.get("published"):
            quality["unpublished_ignored"] += 1
            continue
        groups.setdefault((sid, subj), []).append(m)

    results: dict = {}   # (student_id, subject_id) -> percentage
    published_flag: dict = {}
    for key, docs in groups.items():
        valid = []
        for d in docs:
            pct, had_invalid = record_percentage(d)
            if pct is None:
                quality["invalid_ignored"] += 1 if had_invalid else 0
            else:
                valid.append((_ts(d), d.get("_id", ""), pct, d))
                if had_invalid:
                    quality["invalid_ignored"] += 1
        if not valid:
            continue
        valid.sort(key=lambda t: (t[0], str(t[1])))
        _, _, pct, doc = valid[-1]
        quality["duplicates_ignored"] += len(docs) - 1
        results[key] = pct
        quality["records_used"] += 1
        if not doc.get("published"):
            quality["unpublished_included"] += 1

    # ---- per-student result and eligibility
    student_pct: list[float] = []
    insufficient = 0
    cohort = 0
    for sid, student in students_by_id.items():
        expected = class_subjects.get((student.get("department"), student.get("semester")), set())
        if not expected:
            insufficient += 1
            cohort += 1
            continue
        cohort += 1
        got = [results[(sid, subj)] for subj in expected if (sid, subj) in results]
        needed = max(1, math.ceil(min_coverage * len(expected)))
        if len(got) >= needed:
            student_pct.append(sum(got) / len(got))
        else:
            insufficient += 1

    eligible = len(student_pct)
    passed = sum(1 for p in student_pct if p >= pass_pct)
    failed = eligible - passed
    average = round(sum(student_pct) / eligible, 1) if eligible else None

    counts = {g: 0 for g, _, _ in GRADE_BANDS}
    for p in student_pct:
        counts[grade_for(p)] += 1
    ceilings = [None] + [b[1] for b in GRADE_BANDS[:-1]]
    distribution = [
        {"grade": g, "label": label, "min": floor, "max": (ceilings[i] - 0.1 if ceilings[i] is not None else 100) if i else 100,
         "count": counts[g], "percentage": round(counts[g] / eligible * 100, 1) if eligible else 0.0}
        for i, (g, floor, label) in enumerate(GRADE_BANDS)
    ]

    # ---- per-subject averages (every valid record of the subject, one per student)
    by_subject = []
    for subj_id, subj in sorted(subjects_by_id.items(), key=lambda kv: kv[1].get("name", "")):
        vals = [pct for (sid, sj), pct in results.items() if sj == subj_id]
        if vals:
            by_subject.append({"subject_id": subj_id, "name": subj.get("name"), "code": subj.get("code"),
                               "average_percentage": round(sum(vals) / len(vals), 1), "students_count": len(vals)})

    return {
        "summary": {
            "students_total": cohort, "students_eligible": eligible, "students_insufficient_data": insufficient,
            "average_percentage": average,
            "pass_count": passed, "fail_count": failed,
            "pass_rate": round(passed / eligible * 100, 1) if eligible else None,
            "fail_rate": round(failed / eligible * 100, 1) if eligible else None,
        },
        "grade_distribution": distribution,
        "by_subject": by_subject,
        "config": {
            "pass_percentage": pass_pct, "min_coverage": min_coverage, "default_max_marks": 100,
            "grade_bands": [{"grade": g, "min": f, "label": l} for g, f, l in GRADE_BANDS],
            "method": "Student result = mean of subject percentages; subject % = total score / total maximum. "
                      "Students with marks in fewer than half of their class subjects are excluded from every figure.",
        },
        "data_quality": quality,
    }
