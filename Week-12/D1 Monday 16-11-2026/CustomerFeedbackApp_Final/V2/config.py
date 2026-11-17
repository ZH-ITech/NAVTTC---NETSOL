"""Central settings for V2. Values come from .env (never hardcode secrets)."""
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
