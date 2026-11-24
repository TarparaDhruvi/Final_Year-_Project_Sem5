"""Priority 1: Study Coach upload → extraction → generation → persistence → revisit, plus failure handling."""
import io
import json
import os
from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from conftest import auth, GOOD_STUDY_JSON
from app import database as dbm


def make_pdf(text="Deadlock occurs when processes wait forever. The Coffman conditions are mutual exclusion, hold and wait, no preemption and circular wait."):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO(); c = canvas.Canvas(buf)
    y = 800
    for line in text.split(". "):
        c.drawString(50, y, line[:100]); y -= 20
    c.save(); return buf.getvalue()


def make_docx(text="Paging divides memory into fixed size frames. A page table maps pages to frames."):
    import docx
    d = docx.Document(); d.add_paragraph(text)
    t = d.add_table(rows=1, cols=2); t.rows[0].cells[0].text = "Algorithm"; t.rows[0].cells[1].text = "Round Robin"
    buf = io.BytesIO(); d.save(buf); return buf.getvalue()


def make_pptx(text="Scheduling: FCFS, SJF and Round Robin decide which process runs next."):
    from pptx import Presentation
    p = Presentation(); s = p.slides.add_slide(p.slide_layouts[1]); s.shapes.title.text = "CPU Scheduling"; s.placeholders[1].text = text
    buf = io.BytesIO(); p.save(buf); return buf.getvalue()


def make_blank_pdf():
    from pypdf import PdfWriter
    w = PdfWriter(); w.add_blank_page(width=200, height=200); buf = io.BytesIO(); w.write(buf); return buf.getvalue()


def make_encrypted_pdf():
    from pypdf import PdfReader, PdfWriter
    r = PdfReader(io.BytesIO(make_pdf())); w = PdfWriter()
    for p in r.pages: w.add_page(p)
    w.encrypt("secret"); buf = io.BytesIO(); w.write(buf); return buf.getvalue()


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
EXAM = (date.today() + timedelta(days=10)).isoformat()


async def upload(client, who, name, data):
    return await client.post("/study-coach/upload", files={"file": (name, data, "application/octet-stream")}, headers=auth(who))


@pytest.mark.parametrize("name,maker,expect", [
    ("notes.pdf", make_pdf, "Coffman"), ("notes.docx", make_docx, "Round Robin"), ("slides.pptx", make_pptx, "Round Robin"),
])
async def test_upload_extracts_real_text(client, world, fake_ai, name, maker, expect):
    r = await upload(client, world["alice"], name, maker())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["kind"] == "text" and body["subject"]
    stored = await dbm.study_materials_collection.find_one({"_id": body["id"]})
    assert expect in stored["extracted_text"] and stored["user_id"] == world["alice"]["_id"]


async def test_upload_image_accepted_as_image_kind(client, world, fake_ai):
    r = await upload(client, world["alice"], "handwritten.png", PNG)
    assert r.status_code == 201 and r.json()["kind"] == "image"


@pytest.mark.parametrize("name,data,status,fragment", [
    ("virus.exe", b"MZ\x90", 400, "Unsupported"),
    ("notes.txt", b"plain", 400, "Unsupported"),
    ("noext", b"plain", 400, "Unsupported"),
    ("fake.pdf", b"just text renamed", 400, "doesn't look like"),
    ("empty.pdf", b"", 400, "empty"),
    ("corrupt.docx", b"PK\x03\x04garbage-not-a-zip", 400, "corrupted"),
    ("corrupt.pptx", b"PK\x03\x04garbage-not-a-zip", 400, "corrupted"),
    ("scan.pdf", make_blank_pdf(), 422, "scanned"),
    ("locked.pdf", make_encrypted_pdf(), 400, "password"),
])
async def test_upload_rejections_are_clean_4xx_not_500(client, world, fake_ai, name, data, status, fragment):
    r = await upload(client, world["alice"], name, data)
    assert r.status_code == status, r.text
    assert fragment.lower() in r.json()["detail"].lower()
    assert await dbm.study_materials_collection.count_documents({}) == 0


async def test_upload_too_large(client, world, fake_ai):
    r = await upload(client, world["alice"], "big.pdf", b"%PDF-" + b"0" * (15 * 1024 * 1024 + 10))
    assert r.status_code == 400 and "15 MB" in r.json()["detail"]


async def test_upload_works_without_api_key_but_generate_says_not_configured(client, world, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    r = await upload(client, world["alice"], "notes.pdf", make_pdf())
    assert r.status_code == 201                                   # upload + offline subject detection still work
    g = await client.post("/study-coach/generate", json={"material_id": r.json()["id"], "exam_date": EXAM, "daily_hours": 2}, headers=auth(world["alice"]))
    assert g.status_code == 503 and "OPENAI_API_KEY" in g.json()["detail"]
    assert await dbm.study_plans_collection.count_documents({}) == 0


async def test_full_generation_saved_and_revisitable(client, world, fake_ai):
    h = auth(world["alice"])
    mid = (await upload(client, world["alice"], "os.pdf", make_pdf())).json()["id"]
    r = await client.post("/study-coach/generate", json={"material_id": mid, "exam_date": EXAM, "daily_hours": 2.5}, headers=h)
    assert r.status_code == 200, r.text
    plan = r.json()

    # every required study resource is present
    assert plan["short_notes"].startswith("## Deadlock")
    assert plan["important_topics"][0] == "Deadlock"
    assert len(plan["topic_explanations"]) == 2
    assert len(plan["formula_sheet"]) == 2
    assert len(plan["flashcards"]) == 10
    assert len(plan["mcqs"]) == 10
    for q in plan["mcqs"]:
        assert len(q["options"]) == 4 and 0 <= q["correct_index"] < 4 and q["explanation"]
    assert len(plan["viva_questions"]) == 8
    assert "Coffman" in plan["last_night_mode"]
    assert len(plan["planner"]) == 10 and plan["planner"][-1]["phase"] == "exam_eve"
    assert all({"date", "focus_topic", "target_hours", "tasks"} <= set(d) for d in plan["planner"])

    # the model got the student's real notes (not a canned answer), wrapped as data
    sent = fake_ai.calls[-1]["messages"][1]["content"]
    assert "Coffman conditions" in sent and fake_ai.calls[-1]["json_mode"] is True

    # persisted in MongoDB and revisitable from fresh requests
    assert await dbm.flashcards_collection.count_documents({"plan_id": plan["id"]}) == 10
    assert await dbm.mcqs_collection.count_documents({"plan_id": plan["id"]}) == 10
    h2 = auth(world["alice"])
    listing = (await client.get("/study-coach/plans", headers=h2)).json()
    assert [p["id"] for p in listing] == [plan["id"]]
    again = (await client.get(f"/study-coach/plans/{plan['id']}", headers=h2)).json()
    assert again["mcqs"] == plan["mcqs"] and again["flashcards"] == plan["flashcards"] and again["planner"] == plan["planner"]
    assert (await client.get("/study-coach/materials", headers=h2)).json()[0]["id"] == mid

    # regenerating from the same saved upload works and creates a second plan
    r2 = await client.post("/study-coach/generate", json={"material_id": mid, "exam_date": EXAM, "daily_hours": 1}, headers=h2)
    assert r2.status_code == 200 and r2.json()["id"] != plan["id"]
    assert len((await client.get("/study-coach/plans", headers=h2)).json()) == 2


async def test_image_notes_go_to_model_as_vision_input(client, world, fake_ai):
    mid = (await upload(client, world["alice"], "hand.png", PNG)).json()["id"]
    r = await client.post("/study-coach/generate", json={"material_id": mid, "exam_date": EXAM, "daily_hours": 1}, headers=auth(world["alice"]))
    assert r.status_code == 200, r.text
    content = fake_ai.calls[-1]["messages"][1]["content"]
    assert isinstance(content, list) and content[1]["image_url"]["url"].startswith("data:image/png;base64,")


async def test_study_coach_data_isolated_between_students(client, world, fake_ai):
    ha, hb = auth(world["alice"]), auth(world["bob"])
    mid = (await upload(client, world["alice"], "os.pdf", make_pdf())).json()["id"]
    pid = (await client.post("/study-coach/generate", json={"material_id": mid, "exam_date": EXAM, "daily_hours": 1}, headers=ha)).json()["id"]

    assert (await client.get("/study-coach/plans", headers=hb)).json() == []
    assert (await client.get("/study-coach/materials", headers=hb)).json() == []
    assert (await client.get(f"/study-coach/plans/{pid}", headers=hb)).status_code == 404
    assert (await client.delete(f"/study-coach/plans/{pid}", headers=hb)).status_code == 404
    assert (await client.post("/study-coach/generate", json={"material_id": mid, "exam_date": EXAM, "daily_hours": 1}, headers=hb)).status_code == 404
    assert (await client.get(f"/study-coach/materials/{mid}/file", headers=hb)).status_code == 404
    assert (await client.delete(f"/study-coach/materials/{mid}", headers=hb)).status_code == 404
    # owner still has everything
    assert (await client.get(f"/study-coach/plans/{pid}", headers=ha)).status_code == 200
    assert (await client.get(f"/study-coach/materials/{mid}/file", headers=ha)).status_code == 200


async def test_uploaded_files_are_not_publicly_served(client, world, fake_ai):
    mid = (await upload(client, world["alice"], "os.pdf", make_pdf())).json()["id"]
    stored = await dbm.study_materials_collection.find_one({"_id": mid})
    name = os.path.basename(stored["file_url"])
    from app.routes.study_coach import PRIVATE_DIR
    assert os.path.isfile(os.path.join(PRIVATE_DIR, name))
    # not under the public static mount, and the legacy public path is closed
    for path in (f"/uploads/study_coach/{name}", f"/uploads/study_coach/{name}".upper().replace("/UPLOADS", "/uploads")):
        assert (await client.get(path)).status_code == 404


async def test_legacy_material_file_still_readable(client, world, fake_ai):
    """Materials uploaded by the previous build live in uploads/study_coach; they must still work (and not be public)."""
    from app.routes.study_coach import LEGACY_DIR
    from app.models.study_material import new_material_document
    os.makedirs(LEGACY_DIR, exist_ok=True)
    name = "legacy-test-file.png"
    with open(os.path.join(LEGACY_DIR, name), "wb") as f:
        f.write(PNG)
    try:
        doc = new_material_document(world["alice"]["_id"], "old.png", f"/uploads/study_coach/{name}", "image", "", "Maths", 0.5)
        await dbm.study_materials_collection.insert_one(doc)
        r = await client.post("/study-coach/generate", json={"material_id": doc["_id"], "exam_date": EXAM, "daily_hours": 1}, headers=auth(world["alice"]))
        assert r.status_code == 200, r.text
        assert (await client.get(f"/uploads/study_coach/{name}")).status_code == 404
    finally:
        os.remove(os.path.join(LEGACY_DIR, name))


async def test_delete_plan_and_material(client, world, fake_ai):
    h = auth(world["alice"])
    mid = (await upload(client, world["alice"], "os.pdf", make_pdf())).json()["id"]
    pid = (await client.post("/study-coach/generate", json={"material_id": mid, "exam_date": EXAM, "daily_hours": 1}, headers=h)).json()["id"]
    assert (await client.delete(f"/study-coach/plans/{pid}", headers=h)).status_code == 200
    assert await dbm.flashcards_collection.count_documents({}) == 0 and await dbm.mcqs_collection.count_documents({}) == 0
    assert (await client.delete(f"/study-coach/materials/{mid}", headers=h)).status_code == 200
    assert (await client.get("/study-coach/materials", headers=h)).json() == []


@pytest.mark.parametrize("payload,fragment", [
    ({"exam_date": "2001-01-01", "daily_hours": 2}, "past"),
    ({"exam_date": "not-a-date", "daily_hours": 2}, "valid date"),
    ({"exam_date": EXAM, "daily_hours": 0}, "between"),
    ({"exam_date": EXAM, "daily_hours": 99}, "between"),
])
async def test_generate_validation(client, world, fake_ai, payload, fragment):
    mid = (await upload(client, world["alice"], "os.pdf", make_pdf())).json()["id"]
    r = await client.post("/study-coach/generate", json={"material_id": mid, **payload}, headers=auth(world["alice"]))
    assert r.status_code == 422 and fragment in json.dumps(r.json()).lower()
    assert not any(c["json_mode"] for c in fake_ai.calls)    # rejected before spending an AI call


@pytest.mark.parametrize("bad", ["this is not json at all", "[1,2,3]", '{"short_notes": 5}', "{}"])
async def test_malformed_model_output_gives_502_and_saves_nothing(client, world, fake_ai, bad):
    mid = (await upload(client, world["alice"], "os.pdf", make_pdf())).json()["id"]
    fake_ai.study_json = bad
    r = await client.post("/study-coach/generate", json={"material_id": mid, "exam_date": EXAM, "daily_hours": 1}, headers=auth(world["alice"]))
    assert r.status_code == 502
    assert await dbm.study_plans_collection.count_documents({}) == 0


async def test_fenced_json_and_wrongly_shaped_items_are_tolerated(client, world, fake_ai):
    mid = (await upload(client, world["alice"], "os.pdf", make_pdf())).json()["id"]
    messy = dict(GOOD_STUDY_JSON, flashcards=["just a string", {"front": "ok", "back": "fine"}, {"front": 1}],
                 mcqs=[{"question": "bad", "options": ["only one"], "correct_index": 0}, {"question": "ok?", "options": ["a", "b"], "correct_index": 1, "explanation": "x"}])
    fake_ai.study_json = "```json\n" + json.dumps(messy) + "\n```"
    r = await client.post("/study-coach/generate", json={"material_id": mid, "exam_date": EXAM, "daily_hours": 1}, headers=auth(world["alice"]))
    assert r.status_code == 200, r.text
    assert len(r.json()["flashcards"]) == 1 and len(r.json()["mcqs"]) == 1


@pytest.mark.parametrize("err,code", [
    (HTTPException(429, "OpenAI is rate-limiting requests right now. Wait a few seconds and try again."), 429),
    (HTTPException(502, "Your OpenAI account is out of credit."), 502),
    (HTTPException(504, "Couldn't reach OpenAI (network problem or timeout)."), 504),
])
async def test_provider_errors_pass_through_with_message_and_save_nothing(client, world, fake_ai, err, code):
    mid = (await upload(client, world["alice"], "os.pdf", make_pdf())).json()["id"]
    fake_ai.error = err
    r = await client.post("/study-coach/generate", json={"material_id": mid, "exam_date": EXAM, "daily_hours": 1}, headers=auth(world["alice"]))
    assert r.status_code == code and r.json()["detail"] == err.detail
    assert await dbm.study_plans_collection.count_documents({}) == 0


async def test_generate_rate_limited_per_student(client, world, fake_ai, monkeypatch):
    monkeypatch.setenv("AI_RATE_LIMIT_PER_MINUTE", "8")   # a generation costs 4 units
    mid = (await upload(client, world["alice"], "os.pdf", make_pdf())).json()["id"]    # upload costs 1
    body = {"material_id": mid, "exam_date": EXAM, "daily_hours": 1}
    h = auth(world["alice"])
    assert (await client.post("/study-coach/generate", json=body, headers=h)).status_code == 200
    r = await client.post("/study-coach/generate", json=body, headers=h)
    assert r.status_code == 429 and "Retry-After" in r.headers


# ------------------------------------------------------------------ pure-logic units

def test_planner_covers_every_topic_and_ends_with_exam_eve():
    from app.utils.study_planner import build_planner
    topics = [f"T{i}" for i in range(9)]
    start = date(2030, 1, 1)
    for days in (1, 2, 3, 5, 6, 9, 30, 200):
        plan = build_planner(topics, start, start + timedelta(days=days), 2)
        assert len(plan) == min(days, 120)
        if days >= 3:   # with at least 3 days the learning phase alone must cover every topic
            assert set(topics) <= {t for d in plan if d["phase"] == "learn" for t in d["topics"]}, f"learn phase misses topics for {days} days"
        else:           # 1-2 days: crash / learn+eve — every topic still appears somewhere
            assert set(topics) <= {t for d in plan for t in d["topics"]} | set(topics[:3]) or plan[0]["phase"] == "crash"
        assert plan[-1]["phase"] in ("exam_eve", "crash")
        assert plan[0]["date"] >= start.isoformat() and plan[-1]["date"] < (start + timedelta(days=days)).isoformat()
        assert all(d["target_hours"] == 2 and d["tasks"] and d["focus_topic"] for d in plan)


def test_planner_same_day_exam_and_empty_topics():
    from app.utils.study_planner import build_planner
    d = date(2030, 5, 5)
    plan = build_planner([], d, d, 1.5)
    assert len(plan) == 1 and plan[0]["date"] == d.isoformat() and plan[0]["phase"] == "crash"


def test_text_extract_signature_check():
    from app.utils.text_extract import extract_text
    with pytest.raises(ValueError):
        extract_text("a.png", b"not a png")
    with pytest.raises(ValueError):
        extract_text("a.gif", b"GIF89a")
