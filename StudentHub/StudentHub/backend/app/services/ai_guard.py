"""
services/ai_guard.py
Per-user sliding-window rate limit for AI endpoints, so one student (or a buggy client loop)
can't burn the whole provider quota. In-memory by design: it protects a single backend process;
if you run several workers, each enforces the limit independently (still a useful upper bound).

  AI_RATE_LIMIT_PER_MINUTE   default 20 "cost units" per user per minute
A chat message costs 1 unit; a Study Coach generation costs 4 (it is a much bigger request).
"""
import os
import time
from collections import defaultdict, deque

from fastapi import HTTPException

_WINDOW_SECONDS = 60.0
_events: dict[str, deque] = defaultdict(deque)   # user_id -> deque[(timestamp, cost)]


def _limit() -> int:
    try:
        return max(1, int(os.getenv("AI_RATE_LIMIT_PER_MINUTE", "20")))
    except ValueError:
        return 20


def check_rate_limit(user_id: str, cost: int = 1) -> None:
    now = time.monotonic()
    window = _events[user_id]
    while window and now - window[0][0] > _WINDOW_SECONDS:
        window.popleft()
    used = sum(c for _, c in window)
    if used + cost > _limit():
        retry_after = max(1, int(_WINDOW_SECONDS - (now - window[0][0])) + 1) if window else 1
        raise HTTPException(
            429,
            f"You're sending AI requests too quickly. Please wait about {retry_after} seconds and try again.",
            headers={"Retry-After": str(retry_after)},
        )
    window.append((now, cost))


def reset_for_tests() -> None:
    _events.clear()
