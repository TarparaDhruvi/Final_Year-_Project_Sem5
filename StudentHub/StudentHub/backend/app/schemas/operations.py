"""
schemas/operations.py
Request/response models for Attendance, Assignments, Timetable,
Announcements, and Leave — the day-to-day operational modules.
Date fields reuse utils/dates.reject_past_date for the "no past dates"
rule described in the spec (assignments, exams, leave, announcements).
"""

from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date

from app.utils.dates import reject_past_date


class MarkAttendanceEntry(BaseModel):
    student_id: str   # the students collection's _id (NOT the roll-number student_id field)
    status: str   # "present" | "absent"

    @field_validator("status")
    @classmethod
    def v_status(cls, v):
        if v not in ("present", "absent"):
            raise ValueError("Status must be 'present' or 'absent'.")
        return v


class MarkAttendanceRequest(BaseModel):
    subject_id: str
    date: str
    entries: List[MarkAttendanceEntry]


class UpdateAttendanceRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def v_status(cls, v):
        if v not in ("present", "absent"):
            raise ValueError("Status must be 'present' or 'absent'.")
        return v


class CreateAssignmentRequest(BaseModel):
    title: str
    description: str
    subject_id: str
    due_date: str
    instructions_file_url: Optional[str] = None

    @field_validator("due_date")
    @classmethod
    def v_due_date(cls, v):
        err = reject_past_date(v, "Due date")
        if err: raise ValueError(err)
        return v


class SubmitAssignmentRequest(BaseModel):
    file_url: str


class GradeSubmissionRequest(BaseModel):
    grade: str
    feedback: Optional[str] = None

    @field_validator("grade")
    @classmethod
    def v_grade(cls, v):
        v = (v or "").strip()
        if not v or len(v) > 20:
            raise ValueError("Grade is required (max 20 characters).")
        return v

    @field_validator("feedback")
    @classmethod
    def v_feedback(cls, v):
        if v is not None and len(v) > 2000:
            raise ValueError("Feedback is too long (max 2000 characters).")
        return v


class CreateTimetableSlotRequest(BaseModel):
    day_of_week: str
    start_time: str
    end_time: str
    subject_id: str
    faculty_id: str
    classroom: str
    department: str
    semester: int

    @field_validator("day_of_week")
    @classmethod
    def v_day(cls, v):
        valid = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"}
        if v not in valid:
            raise ValueError(f"Day must be one of {', '.join(sorted(valid))}.")
        return v


class CreateAnnouncementRequest(BaseModel):
    title: str
    message: str
    target_type: str   # "all" | "department" | "semester"
    department: Optional[str] = None
    semester: Optional[int] = None
    scheduled_for: Optional[str] = None   # ISO datetime string; None = publish now

    @field_validator("target_type")
    @classmethod
    def v_target(cls, v):
        if v not in ("all", "department", "semester"):
            raise ValueError("target_type must be 'all', 'department', or 'semester'.")
        return v

    @field_validator("scheduled_for")
    @classmethod
    def v_scheduled(cls, v):
        if v is None:
            return v
        try:
            scheduled_date = date.fromisoformat(v[:10])
        except ValueError:
            raise ValueError("scheduled_for must be a valid ISO date/datetime.")
        err = reject_past_date(scheduled_date, "Scheduled date")
        if err:
            raise ValueError(err)
        return v


class ApplyLeaveRequest(BaseModel):
    reason: str
    from_date: str
    to_date: str

    @field_validator("from_date")
    @classmethod
    def v_from(cls, v):
        err = reject_past_date(v, "Leave start date")
        if err: raise ValueError(err)
        return v

    @field_validator("to_date")
    @classmethod
    def v_to(cls, v, info):
        err = reject_past_date(v, "Leave end date")
        if err: raise ValueError(err)
        if "from_date" in info.data and v < info.data["from_date"]:
            raise ValueError("Leave end date cannot be before the start date.")
        return v


class ReviewLeaveRequest(BaseModel):
    status: str   # "approved" | "rejected"

    @field_validator("status")
    @classmethod
    def v_status(cls, v):
        if v not in ("approved", "rejected"):
            raise ValueError("Status must be 'approved' or 'rejected'.")
        return v
