"""Central settings for V3. Values come from .env (never hardcode secrets)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


FLASK_DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
MAX_UPLOAD_MB = _int_env("MAX_UPLOAD_MB", 5)
MAX_ROWS = _int_env("MAX_ROWS", 2000)
MIN_REVIEW_CHARS = _int_env("MIN_REVIEW_CHARS", 3)
MAX_REVIEW_CHARS = _int_env("MAX_REVIEW_CHARS", 1000)

# --- Executive report (V3) ---
_report = (os.getenv("REPORT_BACKEND") or "auto").strip().lower()
REPORT_BACKEND = _report if _report in ("auto", "openai", "template") else "auto"
OPENAI_MODEL = (os.getenv("OPENAI_MODEL") or "gpt-6-luna").strip()
OPENAI_TIMEOUT_SECONDS = _int_env("OPENAI_TIMEOUT_SECONDS", 60)

_PLACEHOLDER_MARKERS = ("your-", "xxxx", "changeme", "paste")


def get_openai_api_key():
    """Return the API key, or None if it is missing or still a placeholder.

    The key is read only when needed and is never printed or logged.
    """
    key = (os.getenv("OPENAI_API_KEY") or "").strip().strip('"').strip("'")
    if not key or any(marker in key.lower() for marker in _PLACEHOLDER_MARKERS):
        return None
    return key


def openai_configured() -> bool:
    return get_openai_api_key() is not None
