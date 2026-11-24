"""
utils/ai_errors.py
Turns an exception raised by the OpenAI SDK into (http_status, friendly_message).
The generic "the AI returned an error, please try again" is actively misleading for
several common failures — retrying a wrong API key or an empty billing balance can
never succeed — so each class of failure gets a message that says what to actually do.

Matching is by exception class NAME (not isinstance) so this module has no import
dependency on the `openai` package and can be unit-tested without it installed.
"""


def describe_openai_error(exc: Exception) -> tuple[int, str]:
    name = type(exc).__name__
    text = str(exc).lower()

    if name == "AuthenticationError":
        return 502, "OpenAI rejected the API key. Check OPENAI_API_KEY in backend/.env (no quotes, no spaces) and restart the server."
    if name == "PermissionDeniedError":
        return 502, "Your OpenAI account doesn't have permission to use this model. Try a different OPENAI_MODEL in backend/.env."
    if name == "RateLimitError":
        if "insufficient_quota" in text or "quota" in text or "billing" in text:
            return 502, "Your OpenAI account is out of credit. Add a payment method or credits at platform.openai.com, then try again."
        return 429, "OpenAI is rate-limiting requests right now. Wait a few seconds and try again."
    if name == "NotFoundError":
    	print("AI MODEL ERROR DETAILS:", repr(exc))
    	return 502, "Gemini model request failed. Check the backend terminal for details."
    if name in ("APIConnectionError", "APITimeoutError", "Timeout"):
        return 504, "Couldn't reach OpenAI (network problem or timeout). Check the server's internet connection and try again."
    if name == "BadRequestError":
    	print("AI BAD REQUEST DETAILS:", repr(exc))
    	return 400, f"AI request rejected ({name}). Check backend terminal for the exact error."
    if name in ("InternalServerError", "APIStatusError"):
        return 502, "OpenAI is having problems on their side. Try again in a minute."
    return 502, f"The AI service returned an unexpected error ({name}). Please try again."
