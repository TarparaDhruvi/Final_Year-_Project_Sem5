"""
Command-line check that the AI provider is configured correctly — it replaces the old Admin-dashboard
"Test AI connection" card now that AI is student-only. Run from the backend/ folder:

    python -m app.check_ai

It reads backend/.env, makes ONE tiny real request, and prints either "OK" with the latency, or the
exact reason it failed (bad key, no credit, model unavailable, network, rate limit).
"""
import asyncio
import time

from dotenv import load_dotenv

load_dotenv()

from app.services.openai_client import chat_completion, get_model, get_base_url, is_configured   # noqa: E402


async def main() -> int:
    if not is_configured():
        print("FAIL: OPENAI_API_KEY is not set in backend/.env")
        return 1
    started = time.perf_counter()
    try:
        reply = await chat_completion([{"role": "user", "content": "Reply with exactly the word: OK"}], temperature=0, max_tokens=5)
    except Exception as e:   # HTTPException carries the friendly message in .detail
        print(f"FAIL: {getattr(e, 'detail', e)}")
        return 1
    ms = round((time.perf_counter() - started) * 1000)
    print(f"OK: model={get_model()} base_url={get_base_url() or 'default'} replied {reply.strip()!r} in {ms} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
