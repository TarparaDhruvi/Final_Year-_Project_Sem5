"""
routes/reports.py
Admin: Attendance and Marks reports (PDF or Excel), filterable by department/semester.
Faculty: a student-performance report across their own assigned subjects.
Student: their own progress report (PDF).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from typing import Optional, Literal

from app.database import (
    students_collection, users_collection, subjects_collection, attendance_collection,
    marks_collection, faculty_collection, assignments_collection, submissions_collection,
)
from app.auth import require_role
from app.utils.pdf_report import build_table_pdf
from app.utils.excel_report import build_table_excel

router = APIRouter(prefix="/reports", tags=["Reports"])


def _respond(format: str, title: str, subtitle: str, headers: list[str], rows: list[list], filename: str, landscape_mode: bool = False):
    if format == "excel":
        content = build_table_excel(title, headers, rows)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        name = f"{filename}.xlsx"
    else:
        content = build_table_pdf(title, subtitle, headers, rows, landscape_mode)
        media = "application/pdf"
        name = f"{filename}.pdf"
    return Response(content=content, media_type=media, headers={"Content-Disposition": f'attachment; filename="{name}"'})


async def _students_scope(department: Optional[str], semester: Optional[int]) -> list[dict]:
    query = {}
    if department:
        query["department"] = department
    if semester:
        query["semester"] = semester
    return await students_collection.find(query).sort("student_id", 1).to_list(length=10000)


@router.get("/attendance")
async def attendance_report(
    format: Literal["pdf", "excel"] = "pdf",
    department: Optional[str] = None,
    semester: Optional[int] = None,
    admin=Depends(require_role("admin")),
):
    students = await _students_scope(department, semester)
    users = {u["_id"]: u for u in await users_collection.find({"_id": {"$in": [s["user_id"] for s in students]}}).to_list(length=10000)}

    rows = []
    for s in students:
        records = await attendance_collection.find({"student_id": s["_id"]}).to_list(length=5000)
        total = len(records)
        present = sum(1 for r in records if r["status"] == "present")
        pct = round((present / total) * 100, 1) if total else 0.0
        rows.append([users.get(s["user_id"], {}).get("full_name", "—"), s["student_id"], s["department"], s["semester"], present, total, f"{pct}%"])

    subtitle = f"{department or 'All departments'} · {'Semester ' + str(semester) if semester else 'All semesters'}"
    return _respond(format, "Attendance Report", subtitle, ["Student", "Roll No", "Department", "Semester", "Present", "Total", "Attendance %"], rows, "attendance_report")


@router.get("/marks")
async def marks_report(
    format: Literal["pdf", "excel"] = "pdf",
    department: Optional[str] = None,
    semester: Optional[int] = None,
    admin=Depends(require_role("admin")),
):
    students = await _students_scope(department, semester)
    users = {u["_id"]: u for u in await users_collection.find({"_id": {"$in": [s["user_id"] for s in students]}}).to_list(length=10000)}
    subjects = {s["_id"]: s for s in await subjects_collection.find({}).to_list(length=10000)}

    rows = []
    for s in students:
        marks = await marks_collection.find({"student_id": s["_id"]}).to_list(length=500)
        for m in marks:
            subj = subjects.get(m["subject_id"], {})
            rows.append([
                users.get(s["user_id"], {}).get("full_name", "—"), s["student_id"], subj.get("name", "—"),
                m.get("internal"), m.get("practical"), "Yes" if m.get("published") else "No",
            ])

    subtitle = f"{department or 'All departments'} · {'Semester ' + str(semester) if semester else 'All semesters'}"
    return _respond(format, "Marks Report", subtitle, ["Student", "Roll No", "Subject", "Internal", "Practical", "Published"], rows, "marks_report")


@router.get("/my-students")
async def faculty_student_performance(format: Literal["pdf", "excel"] = "pdf", faculty=Depends(require_role("faculty"))):
    fac = await faculty_collection.find_one({"user_id": faculty["_id"]})
    if not fac:
        raise HTTPException(404, "Faculty profile not found.")
    from app.services.faculty_subject_links import subjects_for_faculty
    subjects = await subjects_for_faculty(fac["faculty_id"])

    rows = []
    for subj in subjects:
        students = await students_collection.find({"department": subj["department"], "semester": subj["semester"]}).to_list(length=5000)
        users = {u["_id"]: u for u in await users_collection.find({"_id": {"$in": [s["user_id"] for s in students]}}).to_list(length=5000)}
        assignments = await assignments_collection.find({"subject_id": subj["_id"]}).to_list(length=500)
        for s in students:
            records = await attendance_collection.find({"subject_id": subj["_id"], "student_id": s["_id"]}).to_list(length=500)
            total = len(records)
            present = sum(1 for r in records if r["status"] == "present")
            pct = round((present / total) * 100, 1) if total else 0.0
            submitted = 0
            for a in assignments:
                if await submissions_collection.find_one({"assignment_id": a["_id"], "student_id": s["_id"], "status": {"$in": ["submitted", "graded"]}}):
                    submitted += 1
            marks = await marks_collection.find_one({"subject_id": subj["_id"], "student_id": s["_id"]})
            rows.append([
                users.get(s["user_id"], {}).get("full_name", "—"), s["student_id"], subj["name"], f"{pct}%",
                f"{submitted}/{len(assignments)}", marks.get("internal") if marks else None, marks.get("practical") if marks else None,
            ])

    return _respond(format, "Student Performance Report", f"Faculty: {faculty['full_name']}",
                     ["Student", "Roll No", "Subject", "Attendance %", "Assignments Submitted", "Internal", "Practical"], rows, "student_performance_report", landscape_mode=True)


@router.get("/my-progress")
async def student_progress_report(student=Depends(require_role("student"))):
    s = await students_collection.find_one({"user_id": student["_id"]})
    if not s:
        raise HTTPException(404, "Student profile not found.")
    subjects = await subjects_collection.find({"department": s["department"], "semester": s["semester"]}).to_list(length=200)

    rows = []
    for subj in subjects:
        records = await attendance_collection.find({"subject_id": subj["_id"], "student_id": s["_id"]}).to_list(length=500)
        total = len(records)
        present = sum(1 for r in records if r["status"] == "present")
        pct = round((present / total) * 100, 1) if total else 0.0
        marks = await marks_collection.find_one({"subject_id": subj["_id"], "student_id": s["_id"], "published": True})
        rows.append([subj["name"], f"{pct}%", (marks or {}).get("internal", "—"), (marks or {}).get("practical", "—")])

    return _respond("pdf", "My Progress Report", f"{student['full_name']} · {s['department']} · Semester {s['semester']}",
                     ["Subject", "Attendance %", "Internal Marks", "Practical Marks"], rows, "my_progress_report")
