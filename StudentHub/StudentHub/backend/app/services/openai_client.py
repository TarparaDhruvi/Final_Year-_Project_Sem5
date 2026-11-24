"""
services/openai_client.py
The single place that talks to the AI provider. Every AI feature (StudentHub AI chat, AI Study
Coach subject refinement + generation) goes through chat_completion(), so key checks, timeouts,
retries, and error-to-message mapping are written once and behave the same everywhere.

Provider configuration lives ONLY in backend environment variables:
  OPENAI_API_KEY               required
  OPENAI_MODEL                 default gpt-4o-mini (must support JSON mode; vision for photo notes)
  OPENAI_BASE_URL              optional — point at any OpenAI-compatible endpoint
  AI_REQUEST_TIMEOUT_SECONDS   default 90
Nothing here is ever sent to the browser.
"""
import os
from fastapi import HTTPException

from app.utils.ai_errors import describe_openai_error

MAX_RETRIES = 2   # the SDK retries connection errors / 429 / 5xx with backoff before giving up


def get_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "").strip()


def is_configured() -> bool:
    key = get_api_key()
    return bool(key) and not key.startswith("sk-your")


def get_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


def get_base_url() -> str | None:
    return os.getenv("OPENAI_BASE_URL", "").strip() or None


def get_timeout() -> float:
    try:
        return max(10.0, float(os.getenv("AI_REQUEST_TIMEOUT_SECONDS", "90")))
    except ValueError:
        return 90.0


def require_configured() -> None:
    """Fail fast (before any expensive work) with an actionable message when no key is set."""
    if not is_configured():
        raise HTTPException(503, "AI is not configured on the server. Ask your administrator to set OPENAI_API_KEY in backend/.env and restart the backend.")


async def chat_completion(
    messages: list, *, temperature: float = 0.4, json_mode: bool = False, max_tokens: int | None = None,
) -> str:
    """Returns the assistant's text. Raises HTTPException with a friendly, actionable message on any failure."""
    require_configured()
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise HTTPException(503, "The 'openai' package is not installed. Run: pip install -r requirements.txt")

    client_kwargs = {"api_key": get_api_key(), "timeout": get_timeout(), "max_retries": MAX_RETRIES}
    if get_base_url():
        client_kwargs["base_url"] = get_base_url()
    client = AsyncOpenAI(**client_kwargs)

    kwargs = {"model": get_model(), "messages": messages, "temperature": temperature}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    try:
        resp = await client.chat.completions.create(**kwargs)
    except Exception as e:
        status, message = describe_openai_error(e)
        raise HTTPException(status, message)

    choice = resp.choices[0] if resp.choices else None
    if choice is None:
        raise HTTPException(502, "The AI returned an empty response. Please try again.")
    if getattr(choice, "finish_reason", None) == "content_filter":
        raise HTTPException(422, "The AI declined to process that content. Try different wording or a different file.")
    if json_mode and getattr(choice, "finish_reason", None) == "length":
        raise HTTPException(502, "The AI's answer was cut off because the source was too large. Try a shorter file or fewer pages.")
    return choice.message.content or ""
