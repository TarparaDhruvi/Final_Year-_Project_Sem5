"""
main.py
StudentHub API entry point. Run with:
    uvicorn app.main:app --reload
from inside the backend/ folder (with your venv activated and .env set up).
"""
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from app.database import init_indexes, ping_database
from app.seed import seed_default_admin, seed_demo_data, migrate_study_materials
from app.routes import auth as auth_routes
from app.routes import students as students_routes
from app.routes import faculty as faculty_routes
from app.routes import subjects as subjects_routes
from app.routes import attendance as attendance_routes
from app.routes import assignments as assignments_routes
from app.routes import timetable as timetable_routes
from app.routes import announcements as announcements_routes
from app.routes import leave as leave_routes
from app.routes import notifications as notifications_routes
from app.routes import notes as notes_routes
from app.routes import marks as marks_routes
from app.routes import ai as ai_routes
from app.routes import profile as profile_routes
from app.routes import skill_wallet as skill_wallet_routes
from app.routes import time_capsule as time_capsule_routes
from app.routes import reports as reports_routes
from app.routes import study_coach as study_coach_routes
from app.routes import doubts as doubts_routes
from app.routes import analytics as analytics_routes
from app.routes import bulk_import as bulk_import_routes
from app.routes import search as search_routes
from app.routes import locker as locker_routes
from app.routes import focus as focus_routes
from app.routes import calendar as calendar_routes
from app.routes import faculty_students as faculty_students_routes
from app.routes import activity_hub as activity_hub_routes
from app.services.scheduler import run_scheduler_forever
from app.services.subject_sync import sync_faculty_subject_ids
from app.services.faculty_subject_links import migrate_legacy_assignments
from app.websocket import manager
from app.auth import decode_access_token

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app = FastAPI(
    title="StudentHub API",
    description="AI-Powered Full Stack College Management System",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Study Coach files are private ----------
# Older builds saved Study Coach uploads under /uploads/study_coach, which StaticFiles serves to anyone
# who has the URL. New uploads go to backend/private_uploads (never mounted); this closes the old path
# too. Owners download their originals through GET /study-coach/materials/{id}/file (authenticated).
@app.middleware("http")
async def block_private_upload_paths(request: Request, call_next):
    path = request.url.path.lower()
    if path.startswith("/uploads/study_coach") or path.startswith("/uploads/ai_chat"):
        return JSONResponse(status_code=404, content={"detail": "Not found."})
    return await call_next(request)


# ---------- Never let a Mongo outage crash a request ----------
@app.exception_handler(PyMongoError)
async def mongo_exception_handler(request: Request, exc: PyMongoError):
    return JSONResponse(
        status_code=503,
        content={"detail": "Database unavailable. Please start MongoDB and try again."},
    )


def _check_secrets():
    """Refuse to start in production with the placeholder JWT secrets; just warn in development."""
    weak = [n for n, v in (("JWT_SECRET_KEY", os.getenv("JWT_SECRET_KEY", "")), ("JWT_REFRESH_SECRET_KEY", os.getenv("JWT_REFRESH_SECRET_KEY", "")))
            if not v or v.startswith("change-this") or v.startswith("dev-")]
    if not weak:
        return
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise RuntimeError(f"Refusing to start in production with placeholder secrets: {', '.join(weak)}. Generate real ones with: openssl rand -hex 32")
    print(f"StudentHub WARNING: {', '.join(weak)} still use placeholder values. Fine for local development, never for production.")


@app.on_event("startup")
async def on_startup():
    _check_secrets()
    """
    Retries the MongoDB connection a few times with a short backoff instead
    of letting FastAPI's startup fail outright when Mongo isn't up yet.
    If it still can't connect, the API starts anyway (so /health reports
    the real status) rather than crashing — individual DB-backed requests
    will return a friendly 503 via the handler above until Mongo comes up.
    """
    connected = False
    for attempt in range(1, 6):
        if await ping_database():
            connected = True
            break
        print(f"StudentHub: MongoDB not reachable (attempt {attempt}/5). Retrying in 2s...")
        await asyncio.sleep(2)

    if connected:
        try:
            await init_indexes()
            await migrate_legacy_assignments()   # one-time, non-destructive: legacy subjects.faculty_id -> faculty_subjects links
            await seed_default_admin()
            await seed_demo_data()
            await migrate_study_materials()
            await sync_faculty_subject_ids()   # repair any drift in faculty↔subject links
            asyncio.create_task(run_scheduler_forever())   # deadline reminders + scheduled announcements
        except Exception as e:
            print(f"StudentHub: startup initialization warning — {e}")
    else:
        print("=" * 60)
        print("StudentHub: Database unavailable. Please start MongoDB.")
        print("The API will keep running; requests needing the database")
        print("will return a friendly error until MongoDB is reachable.")
        print("=" * 60)


UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


@app.get("/")
async def root():
    return {"status": "ok", "service": "StudentHub API"}


@app.get("/health")
async def health():
    db_ok = await ping_database()
    return {"status": "healthy" if db_ok else "degraded", "database": "connected" if db_ok else "unavailable"}


# ---------- Routers ----------
app.include_router(auth_routes.router)
app.include_router(students_routes.router)
app.include_router(faculty_routes.router)
app.include_router(faculty_students_routes.router)
app.include_router(activity_hub_routes.router)
app.include_router(subjects_routes.router)
app.include_router(attendance_routes.router)
app.include_router(assignments_routes.router)
app.include_router(timetable_routes.router)
app.include_router(announcements_routes.router)
app.include_router(leave_routes.router)
app.include_router(notifications_routes.router)
app.include_router(notes_routes.router)
app.include_router(marks_routes.router)
app.include_router(ai_routes.router)
app.include_router(profile_routes.router)
app.include_router(skill_wallet_routes.router)
app.include_router(time_capsule_routes.router)
app.include_router(reports_routes.router)
app.include_router(study_coach_routes.router)
app.include_router(doubts_routes.router)
app.include_router(analytics_routes.router)
app.include_router(bulk_import_routes.router)
app.include_router(search_routes.router)
app.include_router(locker_routes.router)
app.include_router(focus_routes.router)
app.include_router(calendar_routes.router)


# ---------- WebSocket ----------
@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    Client connects to ws://<host>/ws/<access_token>. The token is decoded
    to identify the user so notifications can be routed to them specifically.
    """
    try:
        payload = decode_access_token(token)
    except Exception:
        await websocket.close(code=4001)
        return

    user_id = payload.get("sub")
    await manager.connect(user_id, websocket)
    try:
        while True:
            # We don't expect the client to send much; this just keeps
            # the connection alive and lets us receive pings if needed.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
