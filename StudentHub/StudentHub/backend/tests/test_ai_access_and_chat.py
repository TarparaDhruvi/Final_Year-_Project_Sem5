"""Priority 2 + 3: StudentHub AI persistence/isolation and role restrictions on the backend AI endpoints."""
import io
import pytest
from fastapi import HTTPException

from conftest import auth
from app import database as dbm

AI_ENDPOINTS = [
    ("GET", "/ai/status", None),
    ("POST", "/ai/chat", {"message": "hi"}),
    ("GET", "/ai/sessions", None),
    ("GET", "/ai/sessions/abc", None),
    ("DELETE", "/ai/sessions/abc", None),
    ("GET", "/study-coach/materials", None),
    ("GET", "/study-coach/plans", None),
    ("POST", "/study-coach/generate", {"material_id": "x", "exam_date": "2099-01-01", "daily_hours": 1}),
    ("DELETE", "/study-coach/plans/abc", None),
]


@pytest.mark.parametrize("method,path,body", AI_ENDPOINTS)
async def test_admin_and_faculty_get_403_on_every_ai_endpoint(client, world, fake_ai, method, path, body):
    for who in ("admin", "f1"):
        r = await client.request(method, path, json=body, headers=auth(world[who]))
        assert r.status_code == 403, f"{who} {method} {path} -> {r.status_code}"
    assert fake_ai.calls == []   # the provider was never even called


@pytest.mark.parametrize("method,path,body", AI_ENDPOINTS)
async def test_unauthenticated_gets_401(client, world, method, path, body):
    r = await client.request(method, path, json=body)
    assert r.status_code == 401


async def test_upload_endpoints_also_blocked_for_admin_faculty(client, world, fake_ai):
    for who in ("admin", "f1"):
        r = await client.post("/ai/chat/upload", files={"file": ("a.png", b"\x89PNG\r\n\x1a\n" + b"0" * 20)}, headers=auth(world[who]))
        assert r.status_code == 403
        r = await client.post("/study-coach/upload", files={"file": ("a.pdf", b"%PDF-1.4")}, headers=auth(world[who]))
        assert r.status_code == 403


async def test_old_admin_test_endpoint_is_gone(client, world):
    r = await client.post("/ai/test", headers=auth(world["admin"]))
    assert r.status_code in (404, 405)


async def test_chat_multi_message_history_and_restore(client, world, fake_ai):
    h = auth(world["alice"])
    fake_ai.reply = "Answer one"
    r1 = await client.post("/ai/chat", json={"message": "Explain deadlock"}, headers=h)
    assert r1.status_code == 200
    sid = r1.json()["session_id"]
    assert r1.json()["reply"] == "Answer one"

    fake_ai.reply = "Answer two"
    r2 = await client.post("/ai/chat", json={"session_id": sid, "message": "Give an example"}, headers=h)
    assert r2.json()["session_id"] == sid

    # the 2nd call to the provider received the earlier turns (conversation memory)
    sent = fake_ai.calls[-1]["messages"]
    assert [m["role"] for m in sent] == ["system", "user", "assistant", "user"]
    assert sent[1]["content"] == "Explain deadlock" and sent[2]["content"] == "Answer one"

    # "refresh the page / log in again" == brand-new requests with a fresh token
    h2 = auth(world["alice"])
    sessions = (await client.get("/ai/sessions", headers=h2)).json()
    assert len(sessions) == 1 and sessions[0]["id"] == sid and sessions[0]["title"] == "Explain deadlock"
    full = (await client.get(f"/ai/sessions/{sid}", headers=h2)).json()
    assert [m["content"] for m in full["messages"]] == ["Explain deadlock", "Answer one", "Give an example", "Answer two"]

    # a brand-new chat is separate
    r3 = await client.post("/ai/chat", json={"message": "Different topic"}, headers=h2)
    assert r3.json()["session_id"] != sid
    assert len((await client.get("/ai/sessions", headers=h2)).json()) == 2


async def test_regenerate_replaces_last_answer(client, world, fake_ai):
    h = auth(world["alice"])
    fake_ai.reply = "first"
    sid = (await client.post("/ai/chat", json={"message": "q"}, headers=h)).json()["session_id"]
    fake_ai.reply = "second"
    r = await client.post("/ai/chat", json={"session_id": sid, "regenerate": True}, headers=h)
    assert r.json()["reply"] == "second"
    msgs = (await client.get(f"/ai/sessions/{sid}", headers=h)).json()["messages"]
    assert [m["content"] for m in msgs] == ["q", "second"]


async def test_chat_isolation_between_students(client, world, fake_ai):
    sid = (await client.post("/ai/chat", json={"message": "alice secret"}, headers=auth(world["alice"]))).json()["session_id"]
    hb = auth(world["bob"])
    assert (await client.get("/ai/sessions", headers=hb)).json() == []
    assert (await client.get(f"/ai/sessions/{sid}", headers=hb)).status_code == 404
    assert (await client.delete(f"/ai/sessions/{sid}", headers=hb)).status_code == 404
    # bob can't append to alice's chat or regenerate it either
    assert (await client.post("/ai/chat", json={"session_id": sid, "message": "hijack"}, headers=hb)).status_code == 404
    assert (await client.post("/ai/chat", json={"session_id": sid, "regenerate": True}, headers=hb)).status_code == 404
    # alice's chat is untouched
    assert len((await client.get(f"/ai/sessions/{sid}", headers=auth(world["alice"]))).json()["messages"]) == 2


async def test_delete_own_chat(client, world, fake_ai):
    h = auth(world["alice"])
    sid = (await client.post("/ai/chat", json={"message": "q"}, headers=h)).json()["session_id"]
    assert (await client.delete(f"/ai/sessions/{sid}", headers=h)).status_code == 200
    assert (await client.get("/ai/sessions", headers=h)).json() == []


async def test_provider_failure_persists_nothing_and_reports_clean_error(client, world, fake_ai):
    h = auth(world["alice"])
    fake_ai.error = HTTPException(502, "OpenAI is having problems on their side. Try again in a minute.")
    r = await client.post("/ai/chat", json={"message": "hello"}, headers=h)
    assert r.status_code == 502 and "problems" in r.json()["detail"]
    assert (await client.get("/ai/sessions", headers=h)).json() == []


async def test_missing_api_key_gives_clear_503(client, world, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    h = auth(world["alice"])
    assert (await client.get("/ai/status", headers=h)).json() == {"configured": False}
    r = await client.post("/ai/chat", json={"message": "hello"}, headers=h)
    assert r.status_code == 503 and "OPENAI_API_KEY" in r.json()["detail"]


async def test_empty_message_rejected(client, world, fake_ai):
    r = await client.post("/ai/chat", json={"message": "   "}, headers=auth(world["alice"]))
    assert r.status_code == 400
    r = await client.post("/ai/chat", json={"message": "x" * 8001}, headers=auth(world["alice"]))
    assert r.status_code == 422


async def test_rate_limit_returns_429(client, world, fake_ai, monkeypatch):
    monkeypatch.setenv("AI_RATE_LIMIT_PER_MINUTE", "3")
    h = auth(world["alice"])
    codes = [(await client.post("/ai/chat", json={"message": f"m{i}"}, headers=h)).status_code for i in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[3:] == [429, 429]
    # a different student has their own budget
    assert (await client.post("/ai/chat", json={"message": "hi"}, headers=auth(world["bob"]))).status_code == 200


async def test_chat_upload_text_file_and_image_not_stored_as_base64(client, world, fake_ai):
    import docx
    d = docx.Document(); d.add_paragraph("Binary search runs in O(log n)."); buf = io.BytesIO(); d.save(buf)
    h = auth(world["alice"])
    r = await client.post("/ai/chat/upload", data={"message": "Summarise this"},
                          files={"file": ("notes.docx", buf.getvalue(), "application/octet-stream")}, headers=h)
    assert r.status_code == 200, r.text
    sid = r.json()["session_id"]
    assert "Binary search runs in O(log n)" in fake_ai.calls[-1]["messages"][-1]["content"]

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
    r = await client.post("/ai/chat/upload", data={"session_id": sid, "message": "What is in this image?"},
                          files={"file": ("shot.png", png, "image/png")}, headers=h)
    assert r.status_code == 200, r.text
    last_user = fake_ai.calls[-1]["messages"][-1]["content"]
    assert isinstance(last_user, list) and last_user[1]["type"] == "image_url"      # vision input sent to the model...
    stored = await dbm.ai_chat_history_collection.find_one({"_id": sid})
    assert "base64" not in str(stored["messages"])                                   # ...but NOT persisted
    shown = (await client.get(f"/ai/sessions/{sid}", headers=h)).json()["messages"]
    assert shown[2]["content"].endswith("📎 shot.png")


async def test_chat_upload_rejects_bad_files(client, world, fake_ai):
    h = auth(world["alice"])
    r = await client.post("/ai/chat/upload", files={"file": ("virus.exe", b"MZ\x90\x00")}, headers=h)
    assert r.status_code == 400 and "Unsupported" in r.json()["detail"]
    r = await client.post("/ai/chat/upload", files={"file": ("fake.pdf", b"this is plain text")}, headers=h)
    assert r.status_code == 400
    r = await client.post("/ai/chat/upload", files={"file": ("empty.pdf", b"")}, headers=h)
    assert r.status_code == 400
    assert fake_ai.calls == []


async def test_concurrent_appends_do_not_lose_messages(client, world, fake_ai):
    import asyncio
    h = auth(world["alice"])
    sid = (await client.post("/ai/chat", json={"message": "start"}, headers=h)).json()["session_id"]
    await asyncio.gather(*[client.post("/ai/chat", json={"session_id": sid, "message": f"parallel {i}"}, headers=h) for i in range(5)])
    msgs = (await client.get(f"/ai/sessions/{sid}", headers=h)).json()["messages"]
    assert len(msgs) == 2 + 5 * 2
