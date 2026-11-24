"""Part 4 + 5: login for all three roles, error handling, disabled accounts, tokens, and the real forgot-password flow."""
import hashlib
import re
from datetime import datetime, timedelta, timezone

import pytest

from conftest import auth, PASSWORD
from app import database as dbm
from app.auth import create_access_token
from app.services import auth_limits

LOGINS = {
    "student": ("/auth/login/student", lambda w: {"email": "alice@gmail.com", "password": PASSWORD}),
    "faculty": ("/auth/login/faculty", lambda w: {"faculty_id": "1001", "email": "f1@gmail.com", "password": PASSWORD}),
    "admin": ("/auth/login/admin", lambda w: {"admin_id": "ADMIN001", "email": "admin@gmail.com", "password": PASSWORD}),
}


@pytest.mark.parametrize("role", ["student", "faculty", "admin"])
async def test_correct_login_returns_tokens_and_right_role(client, world, role):
    url, body = LOGINS[role]
    r = await client.post(url, json=body(world))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["user"]["role"] == role and data["access_token"] and data["refresh_token"]
    assert "hashed_password" not in str(data)
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200 and me.json()["role"] == role


@pytest.mark.parametrize("role", ["student", "faculty", "admin"])
async def test_wrong_password_unknown_email_and_wrong_id_are_401_and_generic(client, world, role):
    url, body = LOGINS[role]
    msgs = set()
    for mutate in ({"password": "Wrong@12345"}, {"email": "nobody@gmail.com"},
                   {"faculty_id": "9999", "admin_id": "WRONG"} if role != "student" else {"password": "Another@999"}):
        payload = {**body(world), **{k: v for k, v in mutate.items() if k in body(world) or k in ("password", "email")}}
        r = await client.post(url, json=payload)
        assert r.status_code == 401, (role, mutate, r.text)
        msgs.add(r.json()["detail"])
        assert "token" not in r.text.lower() or "access_token" not in r.text
    assert len(msgs) == 1, f"messages must not reveal which field was wrong: {msgs}"   # no account enumeration by default


async def test_missing_or_malformed_fields_are_422_not_a_login(client, world):
    assert (await client.post("/auth/login/student", json={})).status_code == 422
    assert (await client.post("/auth/login/student", json={"email": "alice@gmail.com"})).status_code == 422
    assert (await client.post("/auth/login/student", json={"email": "not-an-email", "password": "x"})).status_code == 422
    assert (await client.post("/auth/login/faculty", json={"email": "f1@gmail.com", "password": PASSWORD})).status_code == 422   # no ID


async def test_role_cannot_be_chosen_by_the_caller(client, world):
    # a faculty account can't log in through the student or admin portal, and vice versa
    assert (await client.post("/auth/login/student", json={"email": "f1@gmail.com", "password": PASSWORD})).status_code == 401
    assert (await client.post("/auth/login/admin", json={"admin_id": "1001", "email": "f1@gmail.com", "password": PASSWORD})).status_code == 401
    assert (await client.post("/auth/login/faculty", json={"faculty_id": "1001", "email": "admin@gmail.com", "password": PASSWORD})).status_code == 401


async def test_reveal_mode_gives_specific_messages_only_when_enabled(client, world, monkeypatch):
    monkeypatch.setenv("AUTH_REVEAL_ACCOUNT_EXISTS", "true")
    r = await client.post("/auth/login/student", json={"email": "alice@gmail.com", "password": "Wrong@12345"})
    assert r.status_code == 401 and r.json()["detail"] == "Incorrect password. Please try again."
    r = await client.post("/auth/login/student", json={"email": "ghost@gmail.com", "password": PASSWORD})
    assert r.json()["detail"] == "Account not found. Please check your email."
    r = await client.post("/auth/login/faculty", json={"faculty_id": "9999", "email": "f1@gmail.com", "password": PASSWORD})
    assert r.json()["detail"] == "Account not found. Please check your Faculty ID."
    r = await client.post("/auth/login/student", json={"email": "f1@gmail.com", "password": PASSWORD})
    assert r.status_code == 403 and "different portal" in r.json()["detail"]


@pytest.mark.parametrize("role", ["student", "faculty", "admin"])
async def test_disabled_account_blocked_with_clear_message_only_after_correct_credentials(client, world, role):
    url, body = LOGINS[role]
    user = world[{"student": "alice", "faculty": "f1", "admin": "admin"}[role]]
    await dbm.users_collection.update_one({"_id": user["_id"]}, {"$set": {"is_active": False}})
    r = await client.post(url, json=body(world))
    assert r.status_code == 403 and "disabled" in r.json()["detail"].lower() and "administrator" in r.json()["detail"].lower()
    # wrong password on a disabled account must NOT reveal that it is disabled
    r = await client.post(url, json={**body(world), "password": "Wrong@12345"})
    assert r.status_code == 401 and "disabled" not in r.json()["detail"].lower()


async def test_unverified_student_cannot_log_in(client, world):
    await dbm.users_collection.update_one({"_id": world["alice"]["_id"]}, {"$set": {"is_verified": False}})
    r = await client.post("/auth/login/student", json=LOGINS["student"][1](world))
    assert r.status_code == 403 and "verify" in r.json()["detail"].lower()


async def test_failed_logins_are_rate_limited_then_recover_on_success_path(client, world, monkeypatch):
    monkeypatch.setenv("LOGIN_MAX_FAILURES", "3")
    bad = {"email": "alice@gmail.com", "password": "Wrong@12345"}
    assert [(await client.post("/auth/login/student", json=bad)).status_code for _ in range(3)] == [401, 401, 401]
    r = await client.post("/auth/login/student", json=bad)
    assert r.status_code == 429 and "Retry-After" in r.headers
    # even the correct password is refused while blocked (stops guessing), another email is unaffected
    assert (await client.post("/auth/login/student", json=LOGINS["student"][1](world))).status_code == 429
    assert (await client.post("/auth/login/student", json={"email": "bob@gmail.com", "password": PASSWORD})).status_code == 200


async def test_successful_login_clears_failed_attempts(client, world, monkeypatch):
    monkeypatch.setenv("LOGIN_MAX_FAILURES", "3")
    bad = {"email": "alice@gmail.com", "password": "Wrong@12345"}
    for _ in range(2):
        await client.post("/auth/login/student", json=bad)
    assert (await client.post("/auth/login/student", json=LOGINS["student"][1](world))).status_code == 200
    for _ in range(2):
        assert (await client.post("/auth/login/student", json=bad)).status_code == 401   # counter was reset


# ------------------------------------------------------------ tokens & route protection

async def test_expired_invalid_and_missing_tokens_are_401(client, world):
    expired = create_access_token({"sub": world["admin"]["_id"], "role": "admin"}, expires_minutes=-5)
    for header in ({"Authorization": f"Bearer {expired}"}, {"Authorization": "Bearer garbage"}, {"Authorization": "Basic abc"}, {}):
        assert (await client.get("/auth/me", headers=header)).status_code == 401, header
        assert (await client.get("/students", headers=header)).status_code == 401


async def test_protected_endpoints_reject_unauthenticated_and_wrong_role(client, world):
    for path in ("/students", "/faculty", "/faculty/assignments", "/analytics/student-performance", "/marks/mine", "/attendance/me", "/study-coach/plans", "/ai/sessions"):
        assert (await client.get(path)).status_code in (401, 404), path    # never 200 without a token
    assert (await client.get("/faculty/assignments", headers=auth(world["f1"]))).status_code == 403
    assert (await client.get("/students", headers=auth(world["alice"]))).status_code == 403


async def test_token_of_a_deleted_or_disabled_user_stops_working(client, world):
    h = auth(world["bob"])
    assert (await client.get("/auth/me", headers=h)).status_code == 200
    await dbm.users_collection.update_one({"_id": world["bob"]["_id"]}, {"$set": {"is_active": False}})
    assert (await client.get("/auth/me", headers=h)).status_code == 403
    await dbm.users_collection.delete_one({"_id": world["bob"]["_id"]})
    assert (await client.get("/auth/me", headers=h)).status_code == 401


# ------------------------------------------------------------ forgot / reset password

@pytest.fixture
def mailbox(monkeypatch):
    """Pretends SMTP is configured and captures what would be emailed (so we can follow the real link)."""
    from app.routes import auth as auth_routes
    sent = []
    monkeypatch.setattr(auth_routes, "email_configured", lambda: True)
    monkeypatch.setattr(auth_routes, "send_password_reset_email", lambda to, name, token: sent.append({"to": to, "token": token}) or True)
    return sent


async def test_forgot_password_without_smtp_is_honest(client, world, monkeypatch):
    from app.routes import auth as auth_routes
    monkeypatch.setattr(auth_routes, "email_configured", lambda: False)
    r = await client.post("/auth/forgot-password", json={"email": "alice@gmail.com"})
    assert r.status_code == 503 and "SMTP_USERNAME" in r.json()["detail"] and "SMTP_APP_PASSWORD" in r.json()["detail"]
    assert await dbm.password_resets_collection.count_documents({}) == 0         # no token created, no fake "sent"


async def test_full_reset_flow_for_every_role(client, world, mailbox):
    for who, email, login_url, body in (
        ("alice", "alice@gmail.com", "/auth/login/student", {}),
        ("f1", "f1@gmail.com", "/auth/login/faculty", {"faculty_id": "1001"}),
        ("admin", "admin@gmail.com", "/auth/login/admin", {"admin_id": "ADMIN001"}),
    ):
        mailbox.clear()
        old_login = await client.post(login_url, json={**body, "email": email, "password": PASSWORD})
        assert old_login.status_code == 200
        r = await client.post("/auth/forgot-password", json={"email": email})
        assert r.status_code == 200 and mailbox[0]["to"] == email
        token = mailbox[0]["token"]

        stored = await dbm.password_resets_collection.find_one({"user_id": world[who]["_id"], "used": False})
        assert stored["token"] == hashlib.sha256(token.encode()).hexdigest() and stored["token"] != token   # only the hash is stored
        assert token not in str(await dbm.password_resets_collection.find({}).to_list(100))

        new_pw = "Brand@New123"
        done = await client.post("/auth/reset-password", json={"token": token, "new_password": new_pw, "confirm_password": new_pw})
        assert done.status_code == 200, done.text
        assert (await client.post(login_url, json={**body, "email": email, "password": PASSWORD})).status_code == 401      # old password dead
        assert (await client.post(login_url, json={**body, "email": email, "password": new_pw})).status_code == 200       # new works
        # sessions from before the reset are revoked
        assert (await client.post("/auth/refresh", json={"refresh_token": old_login.json()["refresh_token"]})).status_code == 401
        # the stored password is a hash, not the plaintext
        assert (await dbm.users_collection.find_one({"_id": world[who]["_id"]}))["hashed_password"].startswith("$2")


async def test_token_is_single_use(client, world, mailbox):
    await client.post("/auth/forgot-password", json={"email": "alice@gmail.com"})
    token = mailbox[0]["token"]
    ok = {"token": token, "new_password": "First@Reset1", "confirm_password": "First@Reset1"}
    assert (await client.post("/auth/reset-password", json=ok)).status_code == 200
    again = await client.post("/auth/reset-password", json={**ok, "new_password": "Second@Reset1", "confirm_password": "Second@Reset1"})
    assert again.status_code == 400 and "invalid or expired" in again.json()["detail"].lower()
    assert (await client.post("/auth/login/student", json={"email": "alice@gmail.com", "password": "First@Reset1"})).status_code == 200


async def test_concurrent_use_of_the_same_token_succeeds_once(client, world, mailbox):
    import asyncio
    await client.post("/auth/forgot-password", json={"email": "alice@gmail.com"})
    token = mailbox[0]["token"]
    pw = "Racing@Reset1"
    results = await asyncio.gather(*[client.post("/auth/reset-password", json={"token": token, "new_password": pw, "confirm_password": pw}) for _ in range(4)])
    assert sorted(r.status_code for r in results).count(200) == 1


async def test_expired_token_is_rejected(client, world, mailbox):
    await client.post("/auth/forgot-password", json={"email": "alice@gmail.com"})
    await dbm.password_resets_collection.update_many({}, {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)}})
    pw = "Expired@Reset1"
    r = await client.post("/auth/reset-password", json={"token": mailbox[0]["token"], "new_password": pw, "confirm_password": pw})
    assert r.status_code == 400 and "expired" in r.json()["detail"].lower()
    assert (await client.post("/auth/login/student", json={"email": "alice@gmail.com", "password": PASSWORD})).status_code == 200   # unchanged


async def test_unknown_and_forged_tokens_rejected(client, world, mailbox):
    pw = "Forged@Reset1"
    for tok in ("totally-made-up", "", hashlib.sha256(b"x").hexdigest()):
        r = await client.post("/auth/reset-password", json={"token": tok, "new_password": pw, "confirm_password": pw})
        assert r.status_code == 400, tok
    # presenting the STORED HASH as if it were the token must not work
    await client.post("/auth/forgot-password", json={"email": "alice@gmail.com"})
    stored = (await dbm.password_resets_collection.find_one({"used": False}))["token"]
    r = await client.post("/auth/reset-password", json={"token": stored, "new_password": pw, "confirm_password": pw})
    assert r.status_code == 400


@pytest.mark.parametrize("new,confirm,fragment", [
    ("short", "short", "8 characters"), ("alllowercase1!", "alllowercase1!", "uppercase"), ("NoNumber!!", "NoNumber!!", "number"),
    ("Valid@Pass1", "Different@Pass1", "do not match"),
])
async def test_reset_validates_password_and_confirmation(client, world, mailbox, new, confirm, fragment):
    await client.post("/auth/forgot-password", json={"email": "alice@gmail.com"})
    r = await client.post("/auth/reset-password", json={"token": mailbox[0]["token"], "new_password": new, "confirm_password": confirm})
    assert r.status_code == 422 and fragment in r.text
    # a rejected password must not burn the token
    ok = await client.post("/auth/reset-password", json={"token": mailbox[0]["token"], "new_password": "Valid@Pass1", "confirm_password": "Valid@Pass1"})
    assert ok.status_code == 200


async def test_no_account_enumeration_and_no_email_for_unknown_or_disabled(client, world, mailbox):
    known = await client.post("/auth/forgot-password", json={"email": "alice@gmail.com"})
    unknown = await client.post("/auth/forgot-password", json={"email": "ghost@gmail.com"})
    assert known.status_code == unknown.status_code == 200 and known.json() == unknown.json()
    assert [m["to"] for m in mailbox] == ["alice@gmail.com"]
    await dbm.users_collection.update_one({"_id": world["bob"]["_id"]}, {"$set": {"is_active": False}})
    r = await client.post("/auth/forgot-password", json={"email": "bob@gmail.com"})
    assert r.status_code == 200 and r.json() == known.json() and len(mailbox) == 1


async def test_new_request_invalidates_the_previous_link(client, world, mailbox):
    await client.post("/auth/forgot-password", json={"email": "alice@gmail.com"})
    await client.post("/auth/forgot-password", json={"email": "alice@gmail.com"})
    first, second = mailbox[0]["token"], mailbox[1]["token"]
    pw = "Newest@Pass1"
    assert (await client.post("/auth/reset-password", json={"token": first, "new_password": pw, "confirm_password": pw})).status_code == 400
    assert (await client.post("/auth/reset-password", json={"token": second, "new_password": pw, "confirm_password": pw})).status_code == 200


async def test_reset_requests_are_rate_limited_per_email(client, world, mailbox, monkeypatch):
    monkeypatch.setenv("RESET_REQUESTS_PER_HOUR", "2")
    codes = [(await client.post("/auth/forgot-password", json={"email": "alice@gmail.com"})).status_code for _ in range(4)]
    assert codes == [200, 200, 429, 429] and len(mailbox) == 2
    # limiter applies equally to unknown emails (can't be used to probe), and doesn't block other addresses
    codes = [(await client.post("/auth/forgot-password", json={"email": "ghost@gmail.com"})).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    assert (await client.post("/auth/forgot-password", json={"email": "bob@gmail.com"})).status_code == 200


async def test_reset_attempts_are_rate_limited(client, world, mailbox, monkeypatch):
    monkeypatch.setenv("RESET_ATTEMPTS_PER_15MIN", "3")
    pw = "Guessing@Pass1"
    codes = [(await client.post("/auth/reset-password", json={"token": f"guess{i}", "new_password": pw, "confirm_password": pw})).status_code for i in range(5)]
    assert codes == [400, 400, 400, 429, 429]


async def test_email_delivery_failure_leaves_no_live_token_and_leaks_nothing(client, world, monkeypatch, capsys):
    from app.routes import auth as auth_routes
    monkeypatch.setattr(auth_routes, "email_configured", lambda: True)
    def boom(*a, **k): raise ConnectionError("smtp down: secret-token-should-not-appear")
    monkeypatch.setattr(auth_routes, "send_password_reset_email", boom)
    r = await client.post("/auth/forgot-password", json={"email": "alice@gmail.com"})
    assert r.status_code == 200 and r.json()["message"].startswith("If that email")
    assert await dbm.password_resets_collection.count_documents({"purpose": "reset_password"}) == 0
    out = capsys.readouterr().out
    assert "ConnectionError" in out and "secret-token-should-not-appear" not in out


async def test_real_send_function_never_prints_the_reset_link(monkeypatch, capsys):
    from app.utils import email as email_util
    monkeypatch.setattr(email_util, "email_configured", lambda: False)
    assert email_util.send_password_reset_email("alice@gmail.com", "Alice", "SUPER-SECRET-TOKEN") is False
    out = capsys.readouterr().out
    assert "SUPER-SECRET-TOKEN" not in out and "withheld" in out
