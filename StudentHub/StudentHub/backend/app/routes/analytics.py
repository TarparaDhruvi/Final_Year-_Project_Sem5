"""
routes/analytics.py
Admin-only analytics that read from existing collections rather than
maintaining separate aggregate tables, so the numbers are always live:
  - Faculty Heatmap: hardest subjects (lowest avg marks), most-viewed notes,
    assignment delay patterns (overdue rate per subject).
  - Silent Student Finder: students with low attendance, frequent missed
    deadlines, or low engagement (no Skill Wallet activity), with a plain-
    language intervention suggestion for each flag.
  - Campus Pulse: attendance trend over the last 14 days, event participation
    (from Skill Wallet 'event' entries), and overall engagement.
"""
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends

from app.database import (
    subjects_collection, assignments_collection, submissions_collection, marks_collection,
    uploaded_notes_collection, students_collection, users_collection, attendance_collection,
    skill_wallet_collection,
)
from app.auth import require_role
from app.utils.timeutil import today_str
from app.services.performance_analytics import compute_performance

router = APIRouter(prefix="/analytics", tags=["Admin Analytics"])


@router.get("/student-performance")
async def student_performance(
    department: Optional[str] = None,
    semester: Optional[int] = None,
    subject_id: Optional[str] = None,
    published_only: bool = False,
    admin=Depends(require_role("admin")),
):
    """Average marks, grade distribution and pass/fail for the Admin dashboard. Aggregates only — no student-level
    data leaves the server. Calculation rules: see services/performance_analytics.py."""
    student_query: dict = {}
    if department:
        student_query["department"] = department
    if semester:
        student_query["semester"] = semester
    subject_query: dict = {}
    if department:
        subject_query["department"] = department
    if semester:
        subject_query["semester"] = semester
    if subject_id:
        subject_query["_id"] = subject_id

    subjects = await subjects_collection.find(subject_query).to_list(length=5000)
    if subject_id:
        # one subject selected: the cohort is exactly the students enrolled in it
        if not subjects:
            students = []
        else:
            sj = subjects[0]
            students = await students_collection.find({"department": sj["department"], "semester": sj["semester"], **student_query}).to_list(length=20000)
    else:
        students = await students_collection.find(student_query).to_list(length=20000)
    marks = await marks_collection.find({
        "student_id": {"$in": [s["_id"] for s in students]}, "subject_id": {"$in": [s["_id"] for s in subjects]},
    }).to_list(length=200000) if students and subjects else []

    result = compute_performance(students, subjects, marks, published_only=published_only)
    result["filters"] = {"department": department, "semester": semester, "subject_id": subject_id, "published_only": published_only}
    return result


@router.get("/faculty-heatmap")
async def faculty_heatmap(admin=Depends(require_role("admin"))):
    subjects = await subjects_collection.find({}).to_list(length=1000)

    difficulty = []
    delays = []
    for subj in subjects:
        marks = await marks_collection.find({"subject_id": subj["_id"], "internal": {"$ne": None}}).to_list(length=5000)
        if marks:
            avg = round(sum(m["internal"] for m in marks) / len(marks), 1)
            difficulty.append({"subject_id": subj["_id"], "subject_name": subj["name"], "avg_internal_marks": avg, "sample_size": len(marks)})

        assignments = await assignments_collection.find({"subject_id": subj["_id"]}).to_list(length=2000)
        if assignments:
            total_due, total_late_or_missing = 0, 0
            for a in assignments:
                subs = await submissions_collection.find({"assignment_id": a["_id"]}).to_list(length=5000)
                total_due += 1
                on_time = any(s["status"] in ("submitted", "graded") and (not s.get("submitted_at") or s["submitted_at"].date().isoformat() <= a["due_date"]) for s in subs)
                if not on_time:
                    total_late_or_missing += 1
            delays.append({"subject_id": subj["_id"], "subject_name": subj["name"], "assignments": total_due, "overdue_or_missed": total_late_or_missing,
                            "delay_rate_pct": round(total_late_or_missing / total_due * 100, 1) if total_due else 0})

    difficulty.sort(key=lambda x: x["avg_internal_marks"])   # hardest (lowest marks) first
    delays.sort(key=lambda x: -x["delay_rate_pct"])

    notes = await uploaded_notes_collection.find({}).sort("views", -1).to_list(length=20)
    most_viewed_notes = [{"id": n["_id"], "title": n["title"], "views": n.get("views", 0)} for n in notes if n.get("views", 0) > 0]

    return {
        "hardest_subjects": difficulty[:10],
        "most_viewed_notes": most_viewed_notes,
        "assignment_delay_patterns": delays[:10],
    }


@router.get("/silent-students")
async def silent_student_finder(admin=Depends(require_role("admin"))):
    students = await students_collection.find({}).to_list(length=10000)
    users = {u["_id"]: u for u in await users_collection.find({"_id": {"$in": [s["user_id"] for s in students]}}).to_list(length=10000)}

    flagged = []
    for s in students:
        reasons = []

        records = await attendance_collection.find({"student_id": s["_id"]}).to_list(length=2000)
        if records:
            pct = round(sum(1 for r in records if r["status"] == "present") / len(records) * 100, 1)
            if pct < 60:
                reasons.append(f"Low attendance ({pct}%)")

        subjects = await subjects_collection.find({"department": s["department"], "semester": s["semester"]}).to_list(length=50)
        missed = 0
        for subj in subjects:
            assignments = await assignments_collection.find({"subject_id": subj["_id"], "due_date": {"$lt": today_str()}}).to_list(length=500)
            for a in assignments:
                if not await submissions_collection.find_one({"assignment_id": a["_id"], "student_id": s["_id"], "status": {"$in": ["submitted", "graded"]}}):
                    missed += 1
        if missed >= 3:
            reasons.append(f"Missed {missed} assignment deadlines")

        xp_count = await skill_wallet_collection.count_documents({"user_id": s["user_id"]})
        if xp_count == 0:
            reasons.append("No recorded engagement (no attendance, submissions, or event participation)")

        if reasons:
            flagged.append({
                "student_id": s["_id"], "roll_no": s["student_id"], "full_name": users.get(s["user_id"], {}).get("full_name", "—"),
                "department": s["department"], "semester": s["semester"], "flags": reasons,
                "suggestion": "Recommend a check-in with their academic advisor or class coordinator.",
            })

    return {"flagged_count": len(flagged), "students": flagged}


@router.get("/campus-pulse")
async def campus_pulse(admin=Depends(require_role("admin"))):
    days = [(date.today() - timedelta(days=i)) for i in range(13, -1, -1)]
    trend = []
    for d in days:
        d_str = d.isoformat()
        records = await attendance_collection.find({"date": d_str}).to_list(length=20000)
        if records:
            pct = round(sum(1 for r in records if r["status"] == "present") / len(records) * 100, 1)
        else:
            pct = None
        trend.append({"date": d_str, "attendance_pct": pct})

    event_count = await skill_wallet_collection.count_documents({"activity": "event"})
    total_students = await students_collection.count_documents({})
    engaged_students = len(await skill_wallet_collection.distinct("user_id"))

    return {
        "attendance_trend_14d": trend,
        "event_participation_count": event_count,
        "total_students": total_students,
        "engaged_students": engaged_students,
        "engagement_rate_pct": round(engaged_students / total_students * 100, 1) if total_students else 0,
    }
