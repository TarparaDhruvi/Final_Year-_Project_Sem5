"""
validators.py
Shared validation rules, enforced on the backend regardless of what the
frontend already checked. Every rule here mirrors the frontend so the
error messages a user sees are consistent everywhere.
"""

import re

NAME_REGEX = re.compile(r"^[A-Za-z ]{3,30}$")
GMAIL_REGEX = re.compile(r"^[a-zA-Z0-9](\.?[a-zA-Z0-9_-]){0,63}@gmail\.com$")
PHONE_REGEX = re.compile(r"^[0-9]{10}$")
ID_REGEX = re.compile(r"^[0-9]+$")

# Password: 8+ chars, 1 upper, 1 lower, 1 digit, 1 special
PASSWORD_UPPER = re.compile(r"[A-Z]")
PASSWORD_LOWER = re.compile(r"[a-z]")
PASSWORD_DIGIT = re.compile(r"[0-9]")
PASSWORD_SPECIAL = re.compile(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]/\\;']")


def validate_name(name: str) -> str | None:
    """Returns an error message, or None if valid."""
    if not name or not NAME_REGEX.match(name.strip()):
        return "Name must be 3–30 letters only (no numbers or special characters)."
    return None


def validate_gmail(email: str) -> str | None:
    if not email or not GMAIL_REGEX.match(email.strip().lower()):
        return "Only Gmail addresses (@gmail.com) are allowed."
    return None


def validate_password(password: str) -> str | None:
    if not password or len(password) < 8:
        return "Password must be at least 8 characters long."
    if not PASSWORD_UPPER.search(password):
        return "Password must include at least one uppercase letter."
    if not PASSWORD_LOWER.search(password):
        return "Password must include at least one lowercase letter."
    if not PASSWORD_DIGIT.search(password):
        return "Password must include at least one number."
    if not PASSWORD_SPECIAL.search(password):
        return "Password must include at least one special character."
    return None


def password_strength_score(password: str) -> int:
    """0-4 strength score, used by the API if the frontend wants server-verified strength."""
    score = 0
    if len(password) >= 8:
        score += 1
    if PASSWORD_UPPER.search(password) and PASSWORD_LOWER.search(password):
        score += 1
    if PASSWORD_DIGIT.search(password):
        score += 1
    if PASSWORD_SPECIAL.search(password):
        score += 1
    return score


def validate_phone(phone: str) -> str | None:
    if not phone or not PHONE_REGEX.match(phone.strip()):
        return "Phone number must be exactly 10 digits."
    return None


def validate_numeric_id(value: str, label: str = "ID") -> str | None:
    if not value or not ID_REGEX.match(value.strip()):
        return f"{label} must contain numbers only."
    return None


def validate_semester(semester: int) -> str | None:
    if semester is None or not (1 <= int(semester) <= 8):
        return "Semester must be between 1 and 8."
    return None
