"""
schemas/academic.py
Request/response models for Student, Faculty, and Subject management
(Admin-only creation/editing). Validation mirrors utils/validators.py.
"""

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from typing import Optional, List

from app.utils.validators import (
    validate_name, validate_gmail, validate_password, validate_phone,
    validate_numeric_id, validate_semester,
)


class CreateStudentRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone: str
    student_id: str
    department: str
    semester: int
    batch: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def v_name(cls, v):
        err = validate_name(v)
        if err: raise ValueError(err)
        return v.strip()

    @field_validator("email")
    @classmethod
    def v_email(cls, v):
        err = validate_gmail(str(v))
        if err: raise ValueError(err)
        return str(v).lower()

    @field_validator("password")
    @classmethod
    def v_password(cls, v):
        err = validate_password(v)
        if err: raise ValueError(err)
        return v

    @field_validator("phone")
    @classmethod
    def v_phone(cls, v):
        err = validate_phone(v)
        if err: raise ValueError(err)
        return v

    @field_validator("student_id")
    @classmethod
    def v_student_id(cls, v):
        err = validate_numeric_id(v, "Student ID")
        if err: raise ValueError(err)
        return v

    @field_validator("semester")
    @classmethod
    def v_semester(cls, v):
        err = validate_semester(v)
        if err: raise ValueError(err)
        return v

    @field_validator("department")
    @classmethod
    def v_department(cls, v):
        v = (v or "").strip()
        if not v or len(v) > 80:
            raise ValueError("Department is required (max 80 characters).")
        return v

    @field_validator("batch")
    @classmethod
    def v_batch(cls, v):
        if v is None: return v
        v = v.strip()
        if len(v) > 20:
            raise ValueError("Batch is too long (max 20 characters).")
        return v or None


class UpdateStudentRequest(BaseModel):
    """Admin edit. Only fields actually sent are changed (so the form can't blank things by accident);
    send `batch: ""` to clear the batch."""
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    student_id: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None
    batch: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def v_name(cls, v):
        if v is None: return v
        err = validate_name(v)
        if err: raise ValueError(err)
        return v.strip()

    @field_validator("email")
    @classmethod
    def v_email(cls, v):
        if v is None: return v
        err = validate_gmail(v)
        if err: raise ValueError(err)
        return v.strip().lower()

    @field_validator("phone")
    @classmethod
    def v_phone(cls, v):
        if v is None: return v
        err = validate_phone(v)
        if err: raise ValueError(err)
        return v.strip()

    @field_validator("student_id")
    @classmethod
    def v_student_id(cls, v):
        if v is None: return v
        err = validate_numeric_id(v, "Student ID")
        if err: raise ValueError(err)
        return v.strip()

    @field_validator("department")
    @classmethod
    def v_department(cls, v):
        if v is None: return v
        v = v.strip()
        if not v or len(v) > 80:
            raise ValueError("Department is required (max 80 characters).")
        return v

    @field_validator("semester")
    @classmethod
    def v_semester(cls, v):
        if v is None: return v
        err = validate_semester(v)
        if err: raise ValueError(err)
        return v

    @field_validator("batch")
    @classmethod
    def v_batch(cls, v):
        if v is None: return v
        v = v.strip()
        if len(v) > 20:
            raise ValueError("Batch is too long (max 20 characters).")
        return v


class StudentStatusRequest(BaseModel):
    is_active: bool


class FacultyStudentEditRequest(BaseModel):
    """What a Faculty member is allowed to change on a student's profile: contact phone and batch ONLY.
    Name, email, ID, department, semester and account status stay Admin-only (sending them is a 422)."""
    model_config = ConfigDict(extra="forbid")
    phone: Optional[str] = None
    batch: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def v_phone(cls, v):
        if v is None: return v
        err = validate_phone(v)
        if err: raise ValueError(err)
        return v.strip()

    @field_validator("batch")
    @classmethod
    def v_batch(cls, v):
        if v is None: return v
        v = v.strip()
        if len(v) > 20:
            raise ValueError("Batch is too long (max 20 characters).")
        return v


class CreateFacultyRequest(BaseModel):
    """
    Admin-only. The Admin sets the Faculty member's password directly
    (no email-delivered temporary password) — Password and Confirm
    Password are both required and validated like every other password
    field in the app (strength + match).
    """
    full_name: str
    email: EmailStr
    phone: str
    faculty_id: str
    department: str
    designation: Optional[str] = None
    password: str
    confirm_password: str

    @field_validator("full_name")
    @classmethod
    def v_name(cls, v):
        err = validate_name(v)
        if err: raise ValueError(err)
        return v.strip()

    @field_validator("email")
    @classmethod
    def v_email(cls, v):
        err = validate_gmail(str(v))
        if err: raise ValueError(err)
        return str(v).lower()

    @field_validator("phone")
    @classmethod
    def v_phone(cls, v):
        err = validate_phone(v)
        if err: raise ValueError(err)
        return v

    @field_validator("faculty_id")
    @classmethod
    def v_faculty_id(cls, v):
        err = validate_numeric_id(v, "Faculty ID")
        if err: raise ValueError(err)
        return v

    @field_validator("password")
    @classmethod
    def v_password(cls, v):
        err = validate_password(v)
        if err: raise ValueError(err)
        return v

    @field_validator("confirm_password")
    @classmethod
    def v_confirm_password(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match.")
        return v


class UpdateFacultyRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def v_name(cls, v):
        if v is None: return v
        err = validate_name(v)
        if err: raise ValueError(err)
        return v.strip()

    @field_validator("phone")
    @classmethod
    def v_phone(cls, v):
        if v is None: return v
        err = validate_phone(v)
        if err: raise ValueError(err)
        return v


class AssignSubjectsRequest(BaseModel):
    subject_ids: List[str]


class AddSubjectsRequest(BaseModel):
    subject_ids: List[str]

    @field_validator("subject_ids")
    @classmethod
    def v_not_empty(cls, v):
        if not v:
            raise ValueError("Select at least one subject.")
        return v


class ReassignSubjectRequest(BaseModel):
    to_faculty_id: str   # the Faculty ID (e.g. "1002") that should take over teaching the subject


class CreateSubjectRequest(BaseModel):
    name: str
    code: str
    department: str
    semester: int
    faculty_id: Optional[str] = None            # legacy single-teacher field: added as ONE of the teachers
    faculty_ids: List[str] = []                 # all teachers of this subject
    credits: int = 3

    @field_validator("semester")
    @classmethod
    def v_semester(cls, v):
        err = validate_semester(v)
        if err: raise ValueError(err)
        return v


class UpdateSubjectRequest(BaseModel):
    name: Optional[str] = None
    faculty_id: Optional[str] = None            # legacy: if given, ADDS this teacher (null is ignored)
    faculty_ids: Optional[List[str]] = None     # if given, becomes the exact set of teachers for this subject
    semester: Optional[int] = None
    credits: Optional[int] = None

    @field_validator("semester")
    @classmethod
    def v_semester(cls, v):
        if v is None: return v
        err = validate_semester(v)
        if err: raise ValueError(err)
        return v
