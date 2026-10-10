"""
Shared OpenRouter API Client Helper for Attend Lens Backend.
Powers:
1. Student 8-Point AI Diagnostic Page
2. Re-run AI Analysis for Class
3. AI Chatbot
4. AI Health Diagnostics (/api/ai/health)
"""
import json
import urllib.request
import urllib.error
from typing import Any, Tuple, Optional
from app.config import get_settings

settings = get_settings()


def is_openrouter_configured() -> bool:
    """Checks if OPENROUTER_API_KEY is configured in backend settings."""
    key = settings.OPENROUTER_API_KEY.strip()
    return bool(key) and key != "YOUR_OPENROUTER_API_KEY_HERE"


def _clean_json_content(content_str: str) -> str:
    """Strips markdown code blocks (```json ... ```) from model output."""
    cleaned = content_str.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # Remove opening fence like ```json or ```
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        # Remove closing fence if present
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def call_openrouter(
    prompt: str,
    system_prompt: Optional[str] = None,
    json_mode: bool = True,
    timeout_seconds: int = 20
) -> Tuple[Optional[Any], Optional[str]]:
    """
    Unified OpenRouter API helper.
    Returns (parsed_result, error_message).
    If parsed_result is not None, error_message is None.
    If OPENROUTER_API_KEY is unconfigured or call fails, returns (None, detailed_error_message).
    """
    if not is_openrouter_configured():
        return None, "OpenRouter API Key missing. Please set OPENROUTER_API_KEY in backend .env and restart the server."

    api_key = settings.OPENROUTER_API_KEY.strip()
    model = settings.OPENROUTER_MODEL.strip() or "openai/gpt-4o-mini"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    # Attempt request with up to 1 retry for JSON parse issues
    max_attempts = 2 if json_mode else 1
    last_error = ""

    for attempt in range(max_attempts):
        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=req_data,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://attendlens.edu",
                    "X-Title": "Attend Lens Academic AI"
                }
            )

            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                raw_resp = resp.read().decode("utf-8")
                resp_json = json.loads(raw_resp)

                choices = resp_json.get("choices", [])
                if not choices:
                    return None, "OpenRouter API returned an empty choices list."

                content_str = choices[0].get("message", {}).get("content", "")
                if not content_str:
                    return None, "OpenRouter API returned empty message content."

                if json_mode:
                    cleaned_str = _clean_json_content(content_str)
                    try:
                        parsed = json.loads(cleaned_str)
                        return parsed, None
                    except json.JSONDecodeError as parse_err:
                        last_error = f"JSON decode error: {str(parse_err)}"
                        print(f"[OPENROUTER JSON PARSE ATTEMPT {attempt + 1}] Failed to parse response: {cleaned_str[:150]}")
                        if attempt == max_attempts - 1:
                            return None, f"Invalid JSON response from model ({model})."
                else:
                    return content_str.strip(), None

        except urllib.error.HTTPError as http_err:
            code = http_err.code
            if code == 401:
                err_msg = "Invalid API Key (HTTP 401 Unauthorized). Check OPENROUTER_API_KEY in backend .env."
            elif code == 402:
                err_msg = "Payment Required / Out of Credits (HTTP 402). Please add credits to your OpenRouter account."
            elif code == 429:
                err_msg = "Rate Limit Reached (HTTP 429). Too many requests to OpenRouter. Please try again shortly."
            elif code == 404:
                err_msg = f"Model Not Found (HTTP 404). Model '{model}' does not exist or is unavailable."
            else:
                err_msg = f"OpenRouter API error (HTTP {code})."
            print(f"[OPENROUTER CLIENT HTTP ERROR] Code {code}: {err_msg}")
            return None, err_msg

        except urllib.error.URLError as url_err:
            err_msg = f"Network Connection Error: {url_err.reason}"
            print(f"[OPENROUTER CLIENT NETWORK ERROR] {err_msg}")
            return None, err_msg

        except Exception as ex:
            err_msg = f"Unexpected error during AI call: {str(ex)}"
            print(f"[OPENROUTER CLIENT EXCEPTION] {err_msg}")
            return None, err_msg

    return None, last_error or "Failed to query OpenRouter API."


def check_openrouter_health() -> dict[str, Any]:
    """
    Makes a small test call to OpenRouter to verify key, credits, and model.
    Returns diagnostic dict for GET /api/ai/health.
    """
    if not is_openrouter_configured():
        return {
            "configured": False,
            "status": "error",
            "model": settings.OPENROUTER_MODEL,
            "error": "OPENROUTER_API_KEY is not configured in backend .env"
        }

    res, err = call_openrouter("Respond with JSON: {\"status\": \"ok\"}", json_mode=True, timeout_seconds=10)
    if err:
        return {
            "configured": True,
            "status": "error",
            "model": settings.OPENROUTER_MODEL,
            "error": err
        }

    return {
        "configured": True,
        "status": "ok",
        "model": settings.OPENROUTER_MODEL,
        "error": None
    }

