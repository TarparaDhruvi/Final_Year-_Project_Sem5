"""
routes/bulk_import.py
Admin bulk-imports students from an .xlsx file. Columns (header row required,
case-insensitive): Full Name, Student ID, Email, Phone, Department, Semester.
Every row is validated with the exact same rules as the single-student form;
a row that fails doesn't stop the others — the response lists exactly which
rows succeeded and which failed, with a reason, so the Admin can fix and
re-upload just the bad ones instead of guessing.
"""
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.database import users_collection, students_collection
from app.auth import require_role, hash_password
from app.models.user import new_user_document
from app.models.student import new_student_document
from app.utils.validators import validate_name, validate_gmail, validate_phone, validate_numeric_id, validate_semester

router = APIRouter(prefix="/students", tags=["Student Management (Admin)"])

REQUIRED_COLUMNS = ["full name", "student id", "email", "phone", "department", "semester"]
DEFAULT_PASSWORD = "Welcome@123"   # students should change this after first login


@router.get("/bulk-import/template")
async def download_template(admin=Depends(require_role("admin"))):
    from openpyxl import Workbook
    from fastapi.responses import Response
    wb = Workbook()
    ws = wb.active
    ws.title = "Students"
    ws.append(["Full Name", "Student ID", "Email", "Phone", "Department", "Semester"])
    ws.append(["Priya Sharma", "2024011", "priya.sharma@gmail.com", "9876543210", "Computer Science", 3])
    buf = io.BytesIO()
    wb.save(buf)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="student_import_template.xlsx"'},
    )


@router.post("/bulk-import")
async def bulk_import_students(file: UploadFile = File(...), admin=Depends(require_role("admin"))):
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(400, "Please upload an .xlsx file (use the template below).")

    content = await file.read()
    try:
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
    except Exception:
        raise HTTPException(400, "Couldn't read that file — please make sure it's a valid .xlsx file.")

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise HTTPException(400, "The file is empty.")

    header = [str(c).strip().lower() if c else "" for c in rows[0]]
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise HTTPException(400, f"Missing required column(s): {', '.join(missing)}. Download the template to see the expected format.")
    col = {name: header.index(name) for name in REQUIRED_COLUMNS}

    created, failed = [], []
    for i, row in enumerate(rows[1:], start=2):
        if row is None or all(c is None for c in row):
            continue   # skip fully blank rows
        try:
            full_name = str(row[col["full name"]] or "").strip()
            student_id = str(row[col["student id"]] or "").strip()
            email = str(row[col["email"]] or "").strip().lower()
            phone = str(row[col["phone"]] or "").strip()
            department = str(row[col["department"]] or "").strip()
            semester_raw = row[col["semester"]]

            for err in (validate_name(full_name), validate_gmail(email), validate_phone(phone), validate_numeric_id(student_id, "Student ID")):
                if err:
                    raise ValueError(err)
            if not department:
                raise ValueError("Department is required.")
            try:
                semester = int(semester_raw)
            except (TypeError, ValueError):
                raise ValueError("Semester must be a number from 1 to 8.")
            err = validate_semester(semester)
            if err:
                raise ValueError(err)

            if await users_collection.find_one({"email": email}) or await users_collection.find_one({"login_id": student_id}):
                raise ValueError("Email or Student ID already exists.")

            if await students_collection.find_one({"student_id": student_id}):
                raise ValueError("Email or Student ID already exists.")
            user_doc = new_user_document(full_name, email, hash_password(DEFAULT_PASSWORD), "student", phone, True, login_id=student_id)
            await users_collection.insert_one(user_doc)
            try:
                await students_collection.insert_one(new_student_document(user_doc["_id"], student_id, department, semester))
            except Exception:
                await users_collection.delete_one({"_id": user_doc["_id"]})   # no orphan login for a failed row
                raise
            created.append({"row": i, "student_id": student_id, "full_name": full_name})
        except Exception as e:
            failed.append({"row": i, "error": str(e)})

    return {
        "message": f"Imported {len(created)} student(s)" + (f", {len(failed)} row(s) failed." if failed else "."),
        "created": created, "failed": failed, "default_password": DEFAULT_PASSWORD if created else None,
    }
