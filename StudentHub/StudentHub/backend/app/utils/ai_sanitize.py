"""
utils/ai_sanitize.py
`response_format={"type": "json_object"}` guarantees the model returns syntactically
valid JSON — it does NOT guarantee that JSON matches the shape we asked for in the
prompt. A flashcard could come back as a plain string instead of {front, back}; an
MCQ could have 3 options instead of 4; a field we expect as a list could come back
as a single string. Any of those would crash routes/study_coach.py (dict-unpacking
a non-dict with **fc) or crash the frontend (.map() on a string, or React refusing
to render a raw object as a child). This module is the one place that turns
"whatever valid JSON the model sent" into exactly the shape the rest of the app
trusts — bad/missing fields degrade gracefully to empty, never raise.
"""


def _as_str(value, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _as_str_list(value, limit: int = 60) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()][:limit]


def sanitize_flashcards(value, limit: int = 30) -> list[dict]:
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if not isinstance(item, dict):
            continue
        front, back = item.get("front"), item.get("back")
        if not isinstance(front, str) or not isinstance(back, str):
            continue
        front, back = front.strip(), back.strip()
        if front and back:
            out.append({"front": front, "back": back})
        if len(out) >= limit:
            break
    return out


def sanitize_mcqs(value, limit: int = 30) -> list[dict]:
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if not isinstance(item, dict):
            continue
        question = item.get("question")
        options = item.get("options")
        correct_index = item.get("correct_index")
        if not isinstance(question, str) or not question.strip():
            continue
        if not isinstance(options, list) or not (2 <= len(options) <= 8):
            continue
        options = [o.strip() if isinstance(o, str) else str(o) for o in options]
        if not all(options):
            continue
        if not isinstance(correct_index, int) or not (0 <= correct_index < len(options)):
            continue   # an MCQ with an out-of-range or missing answer key is worse than useless — drop it
        explanation = item.get("explanation")
        out.append({
            "question": question.strip(), "options": options, "correct_index": correct_index,
            "explanation": explanation.strip() if isinstance(explanation, str) else "",
        })
        if len(out) >= limit:
            break
    return out


def sanitize_topic_explanations(value, limit: int = 30) -> list[dict]:
    """[{topic, explanation}] — anything else the model sends is dropped rather than crashing the page."""
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if not isinstance(item, dict):
            continue
        topic, explanation = item.get("topic"), item.get("explanation")
        if isinstance(topic, str) and isinstance(explanation, str) and topic.strip() and explanation.strip():
            out.append({"topic": topic.strip(), "explanation": explanation.strip()})
        if len(out) >= limit:
            break
    return out


def parse_model_json(raw: str):
    """Parses the model's JSON even if it wrapped it in ```json fences or added a sentence around it.
    Raises ValueError when no JSON object can be recovered."""
    import json
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    raise ValueError("The AI response was not valid JSON.")


def sanitize_study_coach_output(data) -> dict:
    """
    Takes whatever `json.loads()` produced from the model's response (could be a
    dict, a list, a string, or anything else that is still valid JSON) and returns
    a dict guaranteed to have exactly these keys with exactly these types, so every
    caller downstream (Mongo insert, API response, React render) can trust the shape
    without its own defensive checks.
    """
    if not isinstance(data, dict):
        data = {}

    topics = _as_str_list(data.get("important_topics"), limit=30)
    if not topics:
        topics = ["Review notes"]

    return {
        "short_notes": _as_str(data.get("short_notes")),
        "topic_explanations": sanitize_topic_explanations(data.get("topic_explanations")),
        "important_topics": topics,
        "formula_sheet": _as_str_list(data.get("formula_sheet")),
        "viva_questions": _as_str_list(data.get("viva_questions")),
        "last_night_mode": _as_str(data.get("last_night_mode")),
        "flashcards": sanitize_flashcards(data.get("flashcards")),
        "mcqs": sanitize_mcqs(data.get("mcqs")),
    }
