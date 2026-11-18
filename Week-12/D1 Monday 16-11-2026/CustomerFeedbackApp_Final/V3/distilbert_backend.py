"""Optional DistilBERT (SST-2) sentiment backend.

English only. Binary model: it returns POSITIVE or NEGATIVE, never Neutral.
The model is loaded lazily (first use) so VADER-only users never need PyTorch.
"""
import importlib.util
import logging
import os
import threading

from backend_errors import BackendUnavailable
from config import BASE_DIR

log = logging.getLogger("distilbert-backend")

MODEL_ID = "distilbert-base-uncased-finetuned-sst-2-english"
DISTILBERT_LABEL = "DistilBERT SST-2 (local, English, binary Positive/Negative only)"
CACHE_DIR = BASE_DIR / ".hf_cache"

_lock = threading.Lock()
_classifier = None
_load_error = None  # set once if loading fails; restart the app to retry


def dependencies_installed() -> bool:
    """True if torch and transformers can be imported (nothing is imported yet)."""
    return all(importlib.util.find_spec(name) is not None for name in ("torch", "transformers"))


def _model_is_cached() -> bool:
    hub = CACHE_DIR / "hub"
    return hub.exists() and any("sst-2" in p.name for p in hub.glob("models--*"))


def ensure_loaded():
    """Load the model once. Raises BackendUnavailable if that is not possible."""
    global _classifier, _load_error
    with _lock:
        if _classifier is not None:
            return _classifier
        if _load_error:
            raise BackendUnavailable(_load_error)

        # These must be set BEFORE transformers is imported.
        os.environ.setdefault("HF_HOME", str(CACHE_DIR))
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        if _model_is_cached():
            os.environ.setdefault("HF_HUB_OFFLINE", "1")  # use the local copy, no network calls

        try:
            from transformers import pipeline

            _classifier = pipeline("text-classification", model=MODEL_ID, device=-1)
        except Exception as exc:
            _load_error = f"DistilBERT could not be loaded ({type(exc).__name__})."
            log.exception("Could not load DistilBERT")
            raise BackendUnavailable(_load_error) from None
        return _classifier


def distilbert_sentiment(text: str) -> dict:
    """Return the shared sentiment schema (same keys as VADER)."""
    classifier = ensure_loaded()
    out = classifier(text, truncation=True)[0]
    raw = str(out["label"]).upper()
    confidence = float(out["score"])

    if raw.startswith("POS"):
        label, signed, pos, neg = "Positive", confidence, confidence, 1.0 - confidence
    elif raw.startswith("NEG"):
        label, signed, pos, neg = "Negative", -confidence, 1.0 - confidence, confidence
    else:
        raise BackendUnavailable("DistilBERT returned an unexpected label.")

    return {
        "label": label,
        "score": round(signed, 4),      # signed confidence: +conf Positive, -conf Negative
        "positive": round(pos, 3),
        "neutral": 0.0,                 # this model has no Neutral class
        "negative": round(neg, 3),
        "backend": DISTILBERT_LABEL,
    }
