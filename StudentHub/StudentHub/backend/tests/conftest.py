"""
Test harness. There is no real MongoDB in CI/sandbox, so `motor` is swapped for `mongomock-motor`
(an in-memory MongoDB look-alike) BEFORE the app is imported. The real FastAPI app, routers,
authentication and authorization code all run unchanged.

The AI provider is replaced by a test double (see `fake_ai`) because tests must not need a key or the
internet. That means these tests prove StudentHub's own logic (auth, ownership, persistence, validation,
error handling) — they do NOT prove the real OpenAI call works. Use `python -m app.check_ai` for that.
"""
import os
import sys
import json

os.environ["OPENAI_API_KEY"] = "sk-test-not-a-real-key"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-pytest-only-0123456789"
os.environ["JWT_REFRESH_SECRET_KEY"] = "test-refresh-secret-for-pytest-only-0123"
os.environ["ENVIRONMENT"] = "development"
os.environ["AI_RATE_LIMIT_PER_MINUTE"] = "1000"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import motor.motor_asyncio as _motor            # noqa: E402
from mongomock_motor import AsyncMongoMockClient  # noqa: E402
_motor.AsyncIOMotorClient = lambda *a, **k: AsyncMongoMockClient()

import pytest                                   # noqa: E402
import pytest_asyncio                           # noqa: E402
import httpx                                    # noqa: E402

from app.main import app                        # noqa: E402
from app import database as dbm                 # noqa: E402
from app.auth import hash_password, create_access_token   # noqa: E402
from app.models.user import new_user_document   # noqa: E402
from app.models.student import new_student_document   # noqa: E402
from app.models.faculty import new_faculty_document   # noqa: E402
from app.models.subject import new_subject_document   # noqa: E402
from app.services import ai_guard, auth_limits  # noqa: E402

PASSWORD = "Test@12345"
_HASH = hash_password(PASSWORD)


@pytest_asyncio.fixture(autouse=True)
async def clean_db():
    for name in await dbm.db.list_collection_names():
        await dbm.db[name].delete_many({})
    ai_guard.reset_for_tests()
    auth_limits.reset_for_tests()
    # startup (init_indexes) doesn't run under ASGITransport, so create the one index the link logic relies on
    await dbm.faculty_subjects_collection.create_index([("faculty_id", 1), ("subject_id", 1)], unique=True)
    yield


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def auth(user: dict) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': user['_id'], 'role': user['role']})}"}


async def _make_user(name, email, role, login_id, phone="9876543210"):
    u = new_user_document(name, email, _HASH, role, phone, True, login_id=login_id)
    await dbm.users_collection.insert_one(u)
    return u


@pytest_asyncio.fixture
async def world():
    """admin; faculty F1 (teaches DS, CS sem3) and F2 (teaches DBMS CS sem3 + OS CS sem5);
    students: alice & bob (CS sem3), carol (CS sem5), dave (IT sem3)."""
    w = {}
    w["admin"] = await _make_user("Admin User", "admin@gmail.com", "admin", "ADMIN001")

    for key, name, email, fid in (("f1", "Faculty One", "f1@gmail.com", "1001"), ("f2", "Faculty Two", "f2@gmail.com", "1002")):
        u = await _make_user(name, email, "faculty", fid)
        fdoc = new_faculty_document(u["_id"], fid, "Computer Science", "Professor")
        await dbm.faculty_collection.insert_one(fdoc)
        w[key], w[key + "_doc"] = u, fdoc

    from app.services.faculty_subject_links import add_links
    for key, name, code, dept, sem, fid in (
        ("ds", "Data Structures", "CS301", "Computer Science", 3, "1001"),
        ("dbms", "DBMS", "CS302", "Computer Science", 3, "1002"),
        ("os", "Operating Systems", "CS501", "Computer Science", 5, "1002"),
    ):
        w[key] = new_subject_document(name, code, dept, sem)
        await dbm.subjects_collection.insert_one(w[key])
        await add_links(fid, [w[key]["_id"]])

    for key, name, email, sid, dept, sem in (
        ("alice", "Alice Smith", "alice@gmail.com", "2024001", "Computer Science", 3),
        ("bob", "Bob Jones", "bob@gmail.com", "2024002", "Computer Science", 3),
        ("carol", "Carol White", "carol@gmail.com", "2024003", "Computer Science", 5),
        ("dave", "Dave Brown", "dave@gmail.com", "2024004", "Information Technology", 3),
    ):
        u = await _make_user(name, email, "student", sid)
        sdoc = new_student_document(u["_id"], sid, dept, sem)
        await dbm.students_collection.insert_one(sdoc)
        w[key], w[key + "_doc"] = u, sdoc
    return w


# ------------------------------------------------------------------ AI test double

@pytest.fixture
def fake_ai(monkeypatch):
    """Replaces the provider call in both AI modules. `fake_ai.calls` records every message list sent;
    set `fake_ai.reply` (str or callable) / `fake_ai.error` (HTTPException) to script behaviour."""
    from app.routes import ai as ai_routes, study_coach as sc_routes

    class Fake:
        def __init__(self):
            self.calls = []
            self.reply = "Here is a helpful answer."
            self.error = None
            self.study_json = None

    fake = Fake()

    async def _fake(messages, *, temperature=0.4, json_mode=False, max_tokens=None):
        fake.calls.append({"messages": messages, "json_mode": json_mode})
        if fake.error:
            raise fake.error
        if json_mode:
            return fake.study_json if fake.study_json is not None else json.dumps(GOOD_STUDY_JSON)
        # subject-refinement call in the study coach upload (max_tokens=12)
        if max_tokens == 12:
            return "Operating Systems"
        return fake.reply(messages) if callable(fake.reply) else fake.reply

    monkeypatch.setattr(ai_routes, "chat_completion", _fake)
    monkeypatch.setattr(sc_routes, "chat_completion", _fake)
    return fake


GOOD_STUDY_JSON = {
    "short_notes": "## Deadlock\nA deadlock is a state where processes wait forever.",
    "important_topics": ["Deadlock", "Paging", "Scheduling", "Semaphores"],
    "topic_explanations": [{"topic": "Deadlock", "explanation": "Processes wait on each other forever."}, {"topic": "Paging", "explanation": "Memory split into fixed pages."}],
    "formula_sheet": ["Turnaround = Completion - Arrival", "Waiting = Turnaround - Burst"],
    "flashcards": [{"front": f"Term {i}", "back": f"Definition {i}"} for i in range(10)],
    "mcqs": [{"question": f"Q{i}?", "options": ["A", "B", "C", "D"], "correct_index": i % 4, "explanation": f"Because {i}"} for i in range(10)],
    "viva_questions": [f"Viva question {i}?" for i in range(8)],
    "last_night_mode": "Remember the four Coffman conditions.",
}
