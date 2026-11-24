"""
services/auth_limits.py
Small in-memory sliding-window limiter for authentication endpoints (failed logins, password-reset requests
and reset attempts). It protects a single backend process; with several workers each enforces its own limit,
which is still a useful upper bound against guessing and email-bombing.

  LOGIN_MAX_FAILURES        default 10 failed logins per (IP + email) per 15 minutes
  RESET_REQUESTS_PER_HOUR   default 5 reset emails per address per hour (20 per IP)
  RESET_ATTEMPTS_PER_15MIN  default 15 reset-token submissions per IP
"""
import os
import time
from collections import defaultdict, deque

from fastapi import HTTPException

_events: dict[str, deque] = defaultdict(deque)


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _prune(key: str, window: float) -> deque:
    now = time.monotonic()
    q = _events[key]
    while q and now - q[0] > window:
        q.popleft()
    return q


def _retry_after(q: deque, window: float) -> int:
    return max(1, int(window - (time.monotonic() - q[0])) + 1) if q else 1


def _too_many(message: str, wait: int) -> HTTPException:
    minutes = max(1, round(wait / 60))
    return HTTPException(429, f"{message} Please try again in about {minutes} minute{'s' if minutes != 1 else ''}.", headers={"Retry-After": str(wait)})


def check_blocked(bucket: str, key: str, limit: int, window: float, message: str) -> None:
    """Raises 429 if `limit` events were already recorded in the window. Does not record anything."""
    k = f"{bucket}:{key}"
    q = _prune(k, window)
    if len(q) >= limit:
        raise _too_many(message, _retry_after(q, window))


def record(bucket: str, key: str, window: float) -> None:
    k = f"{bucket}:{key}"
    _prune(k, window).append(time.monotonic())


def hit(bucket: str, key: str, limit: int, window: float, message: str) -> None:
    """check_blocked + record in one step (for endpoints where every call counts)."""
    check_blocked(bucket, key, limit, window, message)
    record(bucket, key, window)


def clear(bucket: str, key: str) -> None:
    _events.pop(f"{bucket}:{key}", None)


def reset_for_tests() -> None:
    _events.clear()


# ---- policy helpers used by routes/auth.py ----
LOGIN_WINDOW = 15 * 60
RESET_REQUEST_WINDOW = 60 * 60
RESET_ATTEMPT_WINDOW = 15 * 60


def login_limit() -> int:
    return _env_int("LOGIN_MAX_FAILURES", 10)


def reset_requests_per_hour() -> int:
    return _env_int("RESET_REQUESTS_PER_HOUR", 5)


def reset_attempts_per_window() -> int:
    return _env_int("RESET_ATTEMPTS_PER_15MIN", 15)
