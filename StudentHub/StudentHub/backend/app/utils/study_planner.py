"""
utils/study_planner.py
Turns the AI's ranked "important topics" into a real day-by-day plan between today and the exam.
Pure function (no DB, no AI) so it can be unit-tested. Every important topic is guaranteed to
appear at least once; the last days before the exam switch from learning to revision, and the
final day is the "Last Night" session. Each entry keeps `date`, `focus_topic`, `target_hours`
(used by the Smart Calendar) and adds `phase`, `topics` and concrete `tasks`.
"""
from datetime import date, timedelta

MAX_PLAN_DAYS = 120


def _chunk(topics: list[str], index: int, total_slots: int) -> list[str]:
    """Slice of `topics` for slot `index` of `total_slots`; never empty, covers all topics across slots."""
    t = len(topics)
    start = (index * t) // total_slots
    end = max(start + 1, ((index + 1) * t) // total_slots)
    return topics[start:min(end, t)] or [topics[-1]]


def build_planner(topics: list[str], start: date, exam: date, daily_hours: float, max_days: int = MAX_PLAN_DAYS) -> list[dict]:
    topics = [t for t in topics if t] or ["Review notes"]
    total_days = max(1, (exam - start).days)          # the exam day itself is not a study day
    n = min(total_days, max_days)
    first_day = max(start, exam - timedelta(days=n)) if total_days > max_days else start
    dates = [first_day + timedelta(days=i) for i in range(n)]

    if n == 1:
        phases = ["crash"]
    else:
        revise_total = 1 if n < 6 else max(2, n // 4)   # includes the exam-eve day
        learn = n - revise_total
        phases = ["learn"] * learn + ["revise"] * (revise_total - 1) + ["exam_eve"]
    learn_count = phases.count("learn")
    revise_count = phases.count("revise")

    plan = []
    learn_i = revise_i = 0
    for d, phase in zip(dates, phases):
        if phase == "learn":
            day_topics = _chunk(topics, learn_i, max(learn_count, 1)); learn_i += 1
            tasks = [f"Study and make notes on: {', '.join(day_topics)}", "Write a 5-line summary from memory", "Flip through the matching flashcards"]
            focus = ", ".join(day_topics)
        elif phase == "revise":
            day_topics = _chunk(topics, revise_i, max(revise_count, 1)); revise_i += 1
            tasks = [f"Revise: {', '.join(day_topics)}", "Attempt the MCQ quiz and review wrong answers", "Answer viva questions out loud"]
            focus = f"Revision — {', '.join(day_topics)}"
        elif phase == "exam_eve":
            day_topics = topics[:3]
            tasks = ["Read the Last Night Mode sheet once", "Skim the formula sheet", "Pack what you need and sleep early"]
            focus = "Last-night revision"
        else:  # crash: exam is today/tomorrow, one day only
            day_topics = topics
            tasks = [f"Cover every important topic: {', '.join(topics[:6])}", "Read the Last Night Mode sheet", "Take the MCQ quiz once"]
            focus = "Crash revision — all important topics"
        plan.append({
            "date": d.isoformat(), "focus_topic": focus, "topics": day_topics, "phase": phase,
            "target_hours": daily_hours, "tasks": tasks,
        })
    return plan
