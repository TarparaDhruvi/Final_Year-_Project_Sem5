"""
routes/auth.py
Authentication endpoints, matching the Role Selection -> per-portal flow:

  - Student: the ONLY role that can self-signup. /auth/login/student
    checks email + password, and REQUIRES the account to be email-verified.
  - Faculty: no signup endpoint at all — accounts only come from
    POST /faculty (Admin-only, see routes/faculty.py), which emails the
    Faculty ID + a temporary password. /auth/login/faculty checks
    Faculty ID + email + password all together.
  - Admin: no signup endpoint at all — accounts are pre-seeded (see
    app/seed.py). /auth/login/admin checks Admin ID + email + password.
"""

import asyncio
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, status, Depends

from app.database import users_collection, students_collection, password_resets_collection, refresh_tokens_collection
from app.models.user import new_user_document, public_user
from app.models.student import new_student_document
from app.schemas.auth import (
    SignupRequest,
    StudentLoginRequest,
    FacultyLoginRequest,
    AdminLoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    RefreshTokenRequest,
    TokenResponse,
    MessageResponse,
)
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
)
from app.utils.email import send_verification_email, send_password_reset_email, email_configured
from app.services import auth_limits
from app.services.deadlines import record_login, compute_missed_activity

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------- Student signup (the only self-registration path) ----------

@router.post("/signup", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest):
    if await users_collection.find_one({"email": payload.email}):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    if await users_collection.find_one({"login_id": payload.student_id}):
        raise HTTPException(status_code=409, detail="A student with this Student ID already exists.")

    hashed = hash_password(payload.password)
    user_doc = new_user_document(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hashed,
        role="student",
        phone=payload.phone,
        is_verified=False,
        login_id=payload.student_id,
    )
    await users_collection.insert_one(user_doc)

    student_doc = new_student_document(
        user_id=user_doc["_id"],
        student_id=payload.student_id,
        department=payload.department,
        semester=payload.semester,
    )
    await students_collection.insert_one(student_doc)

    token = secrets.token_urlsafe(32)
    await password_resets_collection.insert_one(
        {
            "token": token,
            "user_id": user_doc["_id"],
            "purpose": "verify_email",
            "used": False,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
        }
    )
    send_verification_email(payload.email, payload.full_name, token)

    return {"message": "Account created. Please check your Gmail inbox to verify your email before logging in."}


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(payload: VerifyEmailRequest):
    record = await password_resets_collection.find_one(
        {"token": payload.token, "purpose": "verify_email", "used": False}
    )
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")

    await users_collection.update_one(
        {"_id": record["user_id"]}, {"$set": {"is_verified": True}}
    )
    await password_resets_collection.update_one({"_id": record["_id"]}, {"$set": {"used": True}})
    return {"message": "Email verified successfully. You can now log in."}


# ---------- Shared login machinery ----------

async def _issue_tokens(user: dict, remember_me: bool, include_missed_activity: bool = False) -> dict:
    access_expiry = 60 * 24 * 7 if remember_me else None  # 7 days if remembered
    access_token = create_access_token({"sub": user["_id"], "role": user["role"]}, access_expiry)
    refresh_token, jti, expires_at = create_refresh_token({"sub": user["_id"]})

    await refresh_tokens_collection.insert_one(
        {
            "jti": jti,
            "user_id": user["_id"],
            "revoked": False,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc),
        }
    )
    await users_collection.update_one(
        {"_id": user["_id"]}, {"$set": {"last_login_at": datetime.now(timezone.utc)}}
    )

    # Smart Deadline Reminder: log this login and, for students, detect
    # what they missed while away — surfaced once, in this login response.
    previous_login = await record_login(user["_id"], user["role"])
    missed_activity = None
    if include_missed_activity:
        missed_activity = await compute_missed_activity(user["_id"], previous_login)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": public_user(user),
        "missed_activity": missed_activity,
    }


# ---------- Login (one authentication path for all three portals) ----------

# Verified against when the account doesn't exist, so "no such account" takes as long as "wrong password"
# and response time can't be used to discover which emails are registered.
_DUMMY_HASH = hash_password("not-a-real-password-StudentHub")

_GENERIC_FAILURE = {
    "student": "Invalid email or password.",
    "faculty": "Invalid Faculty ID, email, or password.",
    "admin": "Invalid Admin ID, email, or password.",
}


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _reveal_accounts() -> bool:
    """AUTH_REVEAL_ACCOUNT_EXISTS=true gives precise messages ("Account not found", "Incorrect password").
    Fine for a private campus deployment; leave it false (default) on a public site, where precise messages
    let anyone test which emails/IDs are registered."""
    return os.getenv("AUTH_REVEAL_ACCOUNT_EXISTS", "false").strip().lower() == "true"


async def _authenticate(request: Request, role: str, email: str, password: str, login_id: str | None = None,
                        id_label: str = "ID") -> dict:
    """Verifies credentials on the backend and returns the user; raises 401/403/429 otherwise.
    The role comes from the portal route being called, and the account must actually have that role in MongoDB."""
    email = str(email).strip().lower()
    key = f"{_client_ip(request)}|{email}"
    auth_limits.check_blocked("login", key, auth_limits.login_limit(), auth_limits.LOGIN_WINDOW,
                              "Too many failed login attempts.")

    user = await users_collection.find_one({"email": email, "role": role})
    password_ok = verify_password(password, user["hashed_password"] if user else _DUMMY_HASH) and user is not None
    id_ok = login_id is None or (user is not None and user.get("login_id") == login_id)

    if not (user and password_ok and id_ok):
        auth_limits.record("login", key, auth_limits.LOGIN_WINDOW)
        if _reveal_accounts():
            if not user:
                other = await users_collection.find_one({"email": email})
                if other:
                    raise HTTPException(403, "This account belongs to a different portal. Please use the correct portal to log in.")
                raise HTTPException(401, "Account not found. Please check your email.")
            if not id_ok:
                raise HTTPException(401, f"Account not found. Please check your {id_label}.")
            raise HTTPException(401, "Incorrect password. Please try again.")
        raise HTTPException(401, _GENERIC_FAILURE[role])

    # Credentials are right, so it is now safe to say why the account can't be used.
    if not user.get("is_active", True):
        raise HTTPException(403, "This account has been disabled. Please contact your administrator.")
    if role == "student" and not user.get("is_verified", False):
        raise HTTPException(403, "Please verify your email before logging in. Check your Gmail inbox.")

    auth_limits.clear("login", key)
    return user


@router.post("/login/student", response_model=TokenResponse)
async def login_student(payload: StudentLoginRequest, request: Request):
    user = await _authenticate(request, "student", payload.email, payload.password)
    return await _issue_tokens(user, payload.remember_me, include_missed_activity=True)


@router.post("/login/faculty", response_model=TokenResponse)
async def login_faculty(payload: FacultyLoginRequest, request: Request):
    user = await _authenticate(request, "faculty", payload.email, payload.password, payload.faculty_id, "Faculty ID")
    return await _issue_tokens(user, payload.remember_me)


@router.post("/login/admin", response_model=TokenResponse)
async def login_admin(payload: AdminLoginRequest, request: Request):
    user = await _authenticate(request, "admin", payload.email, payload.password, payload.admin_id, "Admin ID")
    return await _issue_tokens(user, payload.remember_me)


# ---------- Shared: refresh / logout / forgot / reset / me ----------

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(payload: RefreshTokenRequest):
    decoded = decode_refresh_token(payload.refresh_token)
    record = await refresh_tokens_collection.find_one(
        {"jti": decoded["jti"], "user_id": decoded["sub"], "revoked": False}
    )
    if not record:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked or is invalid.")

    user = await users_collection.find_one({"_id": decoded["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="This account has been disabled.")

    await refresh_tokens_collection.update_one({"_id": record["_id"]}, {"$set": {"revoked": True}})
    access_token = create_access_token({"sub": user["_id"], "role": user["role"]})
    new_refresh_token, jti, expires_at = create_refresh_token({"sub": user["_id"]})
    await refresh_tokens_collection.insert_one(
        {
            "jti": jti,
            "user_id": user["_id"],
            "revoked": False,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc),
        }
    )

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "user": public_user(user),
    }


@router.post("/logout", response_model=MessageResponse)
async def logout(payload: RefreshTokenRequest, current_user: dict = Depends(get_current_user)):
    decoded = decode_refresh_token(payload.refresh_token)
    await refresh_tokens_collection.update_one(
        {"jti": decoded["jti"]}, {"$set": {"revoked": True}}
    )
    return {"message": "Logged out successfully."}


RESET_TOKEN_MINUTES = 15
_FORGOT_GENERIC = "If that email is registered, a password reset link has been sent."


def _hash_token(raw: str) -> str:
    """Only a SHA-256 of the reset token is stored, so a database leak can't be used to reset anyone's password."""
    return hashlib.sha256(raw.encode()).hexdigest()


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(payload: ForgotPasswordRequest, request: Request):
    """Starts a reset. Always answers with the same message whether or not the account exists (no account
    enumeration). The one honest exception is a server that can't send email at all: that is a server setup
    problem, not account information, so it says so instead of pretending an email was sent."""
    email = str(payload.email).strip().lower()
    ip = _client_ip(request)
    auth_limits.hit("forgot-ip", ip, 20, auth_limits.RESET_REQUEST_WINDOW, "Too many password reset requests.")
    auth_limits.hit("forgot-email", email, auth_limits.reset_requests_per_hour(), auth_limits.RESET_REQUEST_WINDOW,
                    "Too many password reset requests for this email.")

    if not email_configured():
        raise HTTPException(503, "Password reset email isn't set up on this server. Ask your administrator to set "
                                 "SMTP_USERNAME and SMTP_APP_PASSWORD in backend/.env and restart the backend.")

    user = await users_collection.find_one({"email": email})
    if not user or not user.get("is_active", True):
        return {"message": _FORGOT_GENERIC}

    # One live reset link per account: a new request invalidates any earlier unused one.
    await password_resets_collection.update_many(
        {"user_id": user["_id"], "purpose": "reset_password", "used": False}, {"$set": {"used": True}})

    raw_token = secrets.token_urlsafe(32)
    await password_resets_collection.insert_one({
        "token": _hash_token(raw_token),          # hash only — the raw token exists solely in the emailed link
        "user_id": user["_id"],
        "purpose": "reset_password",
        "used": False,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_MINUTES),
    })
    try:
        sent = await asyncio.to_thread(send_password_reset_email, user["email"], user["full_name"], raw_token)
    except Exception as exc:   # SMTP outage / bad credentials: log the failure type only — never the link
        print(f"StudentHub: password-reset email failed to send ({type(exc).__name__}).")
        sent = False
    if not sent:
        await password_resets_collection.delete_many({"token": _hash_token(raw_token)})
    return {"message": _FORGOT_GENERIC}


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest, request: Request):
    auth_limits.hit("reset-ip", _client_ip(request), auth_limits.reset_attempts_per_window(), auth_limits.RESET_ATTEMPT_WINDOW,
                    "Too many reset attempts.")
    # Atomically claim the token: it can be used exactly once, even if two requests race.
    record = await password_resets_collection.find_one_and_update(
        {"token": _hash_token(payload.token), "purpose": "reset_password", "used": False},
        {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}},
    )
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link. Please request a new one.")
    if record["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This reset link has expired. Please request a new one.")

    user = await users_collection.find_one({"_id": record["user_id"]})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link. Please request a new one.")

    await users_collection.update_one(
        {"_id": user["_id"]}, {"$set": {"hashed_password": hash_password(payload.new_password), "updated_at": datetime.now(timezone.utc)}})
    # Sign the account out everywhere and void any other outstanding reset links.
    await refresh_tokens_collection.update_many({"user_id": user["_id"]}, {"$set": {"revoked": True}})
    await password_resets_collection.update_many(
        {"user_id": user["_id"], "purpose": "reset_password", "used": False}, {"$set": {"used": True}})
    return {"message": "Password reset successfully. You can now log in with your new password."}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return public_user(current_user)
