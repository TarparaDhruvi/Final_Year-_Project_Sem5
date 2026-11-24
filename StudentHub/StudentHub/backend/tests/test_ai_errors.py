"""AI provider error messages: name the real provider, include the HTTP code, never leak a key."""
import pytest

from app.utils.ai_errors import describe_openai_error, provider_label


def err(name, message="boom", status=None):
    e = type(name, (Exception,), {})(message)
    if status:
        e.status_code = status
    return e


@pytest.mark.parametrize("base,label", [("", "OpenAI"), ("https://generativelanguage.googleapis.com/v1beta/openai/", "Google Gemini"), ("https://api.groq.com/openai/v1", "The AI provider")])
def test_provider_label(monkeypatch, base, label):
    monkeypatch.setenv("OPENAI_BASE_URL", base)
    assert provider_label() == label


def test_server_error_names_gemini_and_shows_status(monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    status, msg = describe_openai_error(err("InternalServerError", "503 UNAVAILABLE: The model is overloaded. key=AIzaSyABCDEFGHIJKLMNOP", 503))
    assert status == 502 and "Google Gemini" in msg and "HTTP 503" in msg and "OpenAI" not in msg
    out = capsys.readouterr().out
    assert "overloaded" in out and "status=503" in out                    # the real reason reaches the terminal...
    assert "AIzaSyABCDEFGHIJKLMNOP" not in out and "[redacted]" in out    # ...with the key removed


@pytest.mark.parametrize("name,status,fragment", [
    ("AuthenticationError", 401, "rejected the API key"), ("RateLimitError", 429, "rate-limiting"),
    ("NotFoundError", 404, "isn't available"), ("APITimeoutError", None, "Couldn't reach"), ("BadRequestError", 400, "couldn't process"),
])
def test_other_classes_still_map(monkeypatch, name, status, fragment):
    monkeypatch.setenv("OPENAI_BASE_URL", "")
    code, msg = describe_openai_error(err(name, "x", status))
    assert fragment in msg and "OpenAI" in msg and code in (400, 429, 502, 504)


def test_quota_rate_limit_is_distinguished_from_a_plain_rate_limit(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    assert describe_openai_error(err("RateLimitError", "You exceeded your current quota", 429))[0] == 502
    assert describe_openai_error(err("RateLimitError", "Too many requests", 429))[0] == 429
