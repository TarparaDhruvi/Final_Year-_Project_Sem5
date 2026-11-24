"""
database.py
Sets up the async MongoDB connection (Motor) and exposes collection handles
used across the whole app. Import `db` anywhere you need to read/write data.

Connection is lazy (Motor doesn't actually connect until the first
operation), so `ping_database()` is used at startup — with retries — to
give a friendly, non-crashing message when MongoDB isn't reachable yet,
instead of letting FastAPI's startup fail outright.
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "studenthub")

client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=3000)
db = client[MONGO_DB_NAME]

# Collection handles — every module imports these instead of raw strings,
# so a rename only has to happen in one place.
users_collection = db["users"]
students_collection = db["students"]
faculty_collection = db["faculty"]
subjects_collection = db["subjects"]
faculty_subjects_collection = db["faculty_subjects"]   # many-to-many: one document per (faculty, subject) pair
schema_migrations_collection = db["schema_migrations"]
attendance_collection = db["attendance"]
assignments_collection = db["assignments"]
submissions_collection = db["submissions"]
marks_collection = db["marks"]
timetable_collection = db["timetable"]
announcements_collection = db["announcements"]
leave_requests_collection = db["leave_requests"]
ai_chat_history_collection = db["ai_chat_history"]
uploaded_notes_collection = db["uploaded_notes"]
study_plans_collection = db["study_plans"]
flashcards_collection = db["flashcards"]
mcqs_collection = db["mcqs"]
skill_wallet_collection = db["skill_wallet"]
time_capsule_collection = db["time_capsule"]
doubts_collection = db["doubts"]
notifications_collection = db["notifications"]
login_history_collection = db["login_history"]
password_resets_collection = db["password_resets"]
refresh_tokens_collection = db["refresh_tokens"]
study_materials_collection = db["study_materials"]
locker_items_collection = db["locker_items"]
events_collection = db["events"]
study_sessions_collection = db["study_sessions"]
alerts_collection = db["alerts_sent"]
contact_messages_collection = db["contact_messages"]


async def ping_database() -> bool:
    """Returns True if MongoDB is reachable right now, False otherwise. Never raises."""
    try:
        await client.admin.command("ping")
        return True
    except Exception:
        return False


async def init_indexes():
    """
    Create the indexes StudentHub relies on for correctness and speed.
    Called once from main.py's startup event.
    """
    await users_collection.create_index("email", unique=True)
    await users_collection.create_index("login_id", unique=True, sparse=True)
    await students_collection.create_index("student_id", unique=True)
    await faculty_collection.create_index("faculty_id", unique=True)
    # Uniqueness is on the PAIR (faculty, subject) — never on the subject alone — so one subject can have many teachers.
    await faculty_subjects_collection.create_index([("faculty_id", 1), ("subject_id", 1)], unique=True)
    await faculty_subjects_collection.create_index("subject_id")
    await password_resets_collection.create_index("token", unique=True)
    await password_resets_collection.create_index("expires_at", expireAfterSeconds=0)
    await refresh_tokens_collection.create_index("expires_at", expireAfterSeconds=0)
    await notifications_collection.create_index([("user_id", 1), ("created_at", -1)])
    await login_history_collection.create_index([("user_id", 1), ("login_at", -1)])
    await study_materials_collection.create_index([("user_id", 1), ("created_at", -1)])
    await study_plans_collection.create_index([("user_id", 1), ("active", 1)])
    await locker_items_collection.create_index([("user_id", 1), ("created_at", -1)])
    await skill_wallet_collection.create_index([("user_id", 1), ("activity", 1)])
    await events_collection.create_index("date")
    await ai_chat_history_collection.create_index([("user_id", 1), ("updated_at", -1)])
    await flashcards_collection.create_index([("plan_id", 1), ("user_id", 1)])
    await mcqs_collection.create_index([("plan_id", 1), ("user_id", 1)])
    await attendance_collection.create_index([("subject_id", 1), ("student_id", 1), ("date", 1)])
    await marks_collection.create_index([("subject_id", 1), ("student_id", 1)])
