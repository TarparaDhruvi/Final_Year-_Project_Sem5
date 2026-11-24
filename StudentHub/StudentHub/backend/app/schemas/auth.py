"""
schemas/auth.py
Pydantic request/response models for every /auth endpoint. Field-level
validators call the shared functions in utils/validators.py so the error
text a client receives always matches the rules described in the docs.

Login is role-specific (three separate schemas/endpoints) to match the
Role Selection -> per-portal login flow: Student logs in with just
Gmail + password; Faculty and Admin additionally confirm their Faculty
ID / Admin ID as a second identity check.
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Literal, Optional

from app.utils.validators import (
    validate_name,
    validate_gmail,
    validate_password,
    validate_phone,
    validate_numeric_id,
    validate_semester,
)


class SignupRequest(BaseModel):
    """Student self-signup only — Faculty and Admin accounts are never created this way."""
    full_name: str
    email: EmailStr
    password: str
    confirm_password: str
    phone: str
    student_id: str
    department: str
    semester: int

    @field_validator("full_name")
    @classmethod
    def check_name(cls, v):
        error = validate_name(v)
        if error:
            raise ValueError(error)
        return v.strip()

    @field_validator("email")
    @classmethod
    def check_gmail(cls, v):
        error = validate_gmail(str(v))
        if error:
            raise ValueError(error)
        return str(v).lower()

    @field_validator("password")
    @classmethod
    def check_password(cls, v):
        error = validate_password(v)
        if error:
            raise ValueError(error)
        return v

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v):
        error = validate_phone(v)
        if error:
            raise ValueError(error)
        return v

    @field_validator("student_id")
    @classmethod
    def check_student_id(cls, v):
        error = validate_numeric_id(v, "Student ID")
        if error:
            raise ValueError(error)
        return v

    @field_validator("department")
    @classmethod
    def check_department(cls, v):
        if not v or not v.strip():
            raise ValueError("Department is required.")
        return v.strip()

    @field_validator("semester")
    @classmethod
    def check_semester(cls, v):
        error = validate_semester(v)
        if error:
            raise ValueError(error)
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match.")
        return v


class StudentLoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class FacultyLoginRequest(BaseModel):
    faculty_id: str
    email: EmailStr
    password: str
    remember_me: bool = False

    @field_validator("faculty_id")
    @classmethod
    def check_faculty_id(cls, v):
        error = validate_numeric_id(v, "Faculty ID")
        if error:
            raise ValueError(error)
        return v


class AdminLoginRequest(BaseModel):
    admin_id: str
    email: EmailStr
    password: str
    remember_me: bool = False

    @field_validator("admin_id")
    @classmethod
    def check_admin_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Admin ID is required.")
        return v.strip()


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v):
        error = validate_password(v)
        if error:
            raise ValueError(error)
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match.")
        return v


class VerifyEmailRequest(BaseModel):
    token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    user: dict
    missed_activity: Optional[dict] = None


class MessageResponse(BaseModel):
    message: str
