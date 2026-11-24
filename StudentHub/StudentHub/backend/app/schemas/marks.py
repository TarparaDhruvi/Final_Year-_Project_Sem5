"""schemas/marks.py — request models for internal/practical marks entry + publishing."""
from pydantic import BaseModel, field_validator
from typing import Optional


class SetMarksRequest(BaseModel):
    student_id: str
    subject_id: str
    internal: Optional[float] = None
    practical: Optional[float] = None

    @field_validator("internal", "practical")
    @classmethod
    def v_range(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError("Marks must be between 0 and 100.")
        return v
