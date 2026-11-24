"""
models/user.py
The `users` collection is the single source of truth for authentication
and role. Role-specific profile data (roll number, department, subjects
taught, etc.) lives in the separate `students` / `faculty` collections,
keyed by the same user_id — this keeps auth concerns and profile
concerns cleanly separated.
"""

import uuid
from datetime import datetime, timezone

ROLES = ("admin", "faculty", "student")


def new_user_document(
    full_name: str,
    email: str,
    hashed_password: str,
    role: str,
    phone: str | None = None,
    is_verified: bool = False,
    login_id: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": str(uuid.uuid4()),
        "full_name": full_name,
        "email": email,
        "hashed_password": hashed_password,
        "role": role,
        "phone": phone,
        # The role-specific ID used at login: student_id for students,
        # faculty_id for faculty, admin_id for admins. Kept on the user
        # document itself so role-specific login can verify it with a
        # single lookup instead of joining to students/faculty.
        "login_id": login_id,
        "avatar_url": None,
        "is_verified": is_verified,
        "is_active": True,
        "theme_preference": "light",
        "created_at": now,
        "updated_at": now,
        "last_login_at": None,
    }


def public_user(user: dict) -> dict:
    """Strips sensitive fields before sending a user object to the client."""
    return {
        "id": user["_id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "role": user["role"],
        "login_id": user.get("login_id"),
        "phone": user.get("phone"),
        "avatar_url": user.get("avatar_url"),
        "is_verified": user.get("is_verified", False),
        "theme_preference": user.get("theme_preference", "light"),
    }
