"""
routes/profile.py
Profile system for every role: view profile (with role-specific academic
details), edit profile, upload a profile photo, and change password.
"""

import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, field_validator
from typing import Optional

from app.database import users_collection, students_collection, faculty_collection
from app.auth import get_current_user, hash_password, verify_password
from app.models.user import public_user
from app.utils.validators import validate_name, validate_phone, validate_password

router = APIRouter(prefix="/profile", tags=["Profile"])

AVATAR_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_AVATAR_BYTES = 2 * 1024 * 1024


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = None   # faculty only
    batch: Optional[str] = None         # student only

    @field_validator("full_name")
    @classmethod
    def v_name(cls, v):
        if v is None:
            return v
        err = validate_name(v)
        if err:
            raise ValueError(err)
        return v.strip()

    @field_validator("phone")
    @classmethod
    def v_phone(cls, v):
        if v is None or v == "":
            return None
        err = validate_phone(v)
        if err:
            raise ValueError(err)
        return v.strip()


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def v_new(cls, v):
        err = validate_password(v)
        if err:
            raise ValueError(err)
        return v

    @field_validator("confirm_password")
    @classmethod
    def v_match(cls, v, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match.")
        return v


async def _profile_payload(user: dict) -> dict:
    data = public_user(user)
    details: dict = {}
    if user["role"] == "student":
        s = await students_collection.find_one({"user_id": user["_id"]})
        if s:
            details = {"student_id": s["student_id"], "department": s["department"], "semester": s["semester"], "batch": s.get("batch")}
    elif user["role"] == "faculty":
        f = await faculty_collection.find_one({"user_id": user["_id"]})
        if f:
            details = {"faculty_id": f["faculty_id"], "department": f["department"], "designation": f.get("designation")}
    else:
        details = {"admin_id": user.get("login_id")}
    data["details"] = details
    return data


@router.get("")
async def get_profile(user: dict = Depends(get_current_user)):
    return await _profile_payload(user)


@router.put("")
async def update_profile(payload: UpdateProfileRequest, user: dict = Depends(get_current_user)):
    fields = payload.model_fields_set
    user_updates = {}
    if "full_name" in fields and payload.full_name:
        user_updates["full_name"] = payload.full_name
    if "phone" in fields:
        user_updates["phone"] = payload.phone
    if user_updates:
        user_updates["updated_at"] = datetime.now(timezone.utc)
        await users_collection.update_one({"_id": user["_id"]}, {"$set": user_updates})

    if user["role"] == "faculty" and "designation" in fields:
        await faculty_collection.update_one({"user_id": user["_id"]}, {"$set": {"designation": payload.designation or None}})
    if user["role"] == "student" and "batch" in fields:
        await students_collection.update_one({"user_id": user["_id"]}, {"$set": {"batch": payload.batch or None}})

    fresh = await users_collection.find_one({"_id": user["_id"]})
    return await _profile_payload(fresh)


@router.post("/photo")
async def upload_photo(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(400, "Please upload a JPG, PNG, or WEBP image.")
    contents = await file.read()
    if len(contents) > MAX_AVATAR_BYTES:
        raise HTTPException(400, "Image is too large. Maximum size is 2 MB.")
    if not contents:
        raise HTTPException(400, "The uploaded file is empty.")

    stored = f"{re.sub(r'[^a-zA-Z0-9-]', '', user['_id'])[:36]}-{uuid.uuid4().hex[:8]}{ext}"
    with open(os.path.join(AVATAR_DIR, stored), "wb") as f:
        f.write(contents)

    # Remove the previous avatar file (best effort) so uploads don't pile up.
    old = user.get("avatar_url")
    if old and old.startswith("/uploads/avatars/"):
        try:
            os.remove(os.path.join(AVATAR_DIR, os.path.basename(old)))
        except OSError:
            pass

    await users_collection.update_one({"_id": user["_id"]}, {"$set": {"avatar_url": f"/uploads/avatars/{stored}"}})
    fresh = await users_collection.find_one({"_id": user["_id"]})
    return await _profile_payload(fresh)


@router.delete("/photo")
async def remove_photo(user: dict = Depends(get_current_user)):
    old = user.get("avatar_url")
    if old and old.startswith("/uploads/avatars/"):
        try:
            os.remove(os.path.join(AVATAR_DIR, os.path.basename(old)))
        except OSError:
            pass
    await users_collection.update_one({"_id": user["_id"]}, {"$set": {"avatar_url": None}})
    fresh = await users_collection.find_one({"_id": user["_id"]})
    return await _profile_payload(fresh)


@router.post("/change-password")
async def change_password(payload: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    if not verify_password(payload.current_password, user["hashed_password"]):
        raise HTTPException(400, "Current password is incorrect.")
    if payload.current_password == payload.new_password:
        raise HTTPException(400, "New password must be different from your current password.")
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"hashed_password": hash_password(payload.new_password), "updated_at": datetime.now(timezone.utc)}},
    )
    return {"message": "Password changed successfully."}
