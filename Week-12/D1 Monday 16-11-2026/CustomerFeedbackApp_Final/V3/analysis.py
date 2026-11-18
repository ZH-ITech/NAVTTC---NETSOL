"""Single-review analysis pipeline. Reused unchanged by later versions."""
import distilbert_backend
from backend_errors import BackendUnavailable
from categories import CATEGORY_METHOD_LABEL, detect_complaint_categories
from config import MAX_REVIEW_CHARS, MIN_REVIEW_CHARS
from nlp_backends import YAKE_LABEL, vader_sentiment, yake_keyphrases

# A backend is listed when it can be used. DistilBERT is listed when torch and
# transformers are installed; the model itself loads on first use. "azure" is added in V3.
SENTIMENT_BACKENDS = {"vader": vader_sentiment}
if distilbert_backend.dependencies_installed():
    SENTIMENT_BACKENDS["distilbert"] = distilbert_backend.distilbert_sentiment

BACKEND_LIMITATIONS = {
    "vader": [
        "VADER is an English lexicon tool: it can miss sarcasm, negation and domain wording "
        "(for example 'stopped working' may score Neutral).",
    ],
    "distilbert": [
        "DistilBERT SST-2 is an English binary model (Positive/Negative only). It has no Neutral class, "
        "so neutral or mixed reviews are forced into one of two labels.",
        "It was fine-tuned on movie-review sentences, not product reviews. Its confidence (often close to 1.0) "
        "is not a measure of correctness.",
        "Its average score uses signed confidence, so it is not comparable with VADER's compound score.",
    ],
}
CATEGORY_LIMITATION = (
    "Complaint categories come from keyword rules: they can miss unusual wording, "
    "mis-handle negation, and over-assign categories when sentiment is Negative."
)


def limitations_for(backend: str) -> list:
    return BACKEND_LIMITATIONS.get(backend, []) + [CATEGORY_LIMITATION]


class InvalidReviewError(ValueError):
    """Raised when the submitted review text is not usable."""


def validate_review(text) -> str:
    if text is None or not str(text).strip():
        raise InvalidReviewError("Please enter a review.")
    cleaned = " ".join(str(text).split())
    if len(cleaned) < MIN_REVIEW_CHARS:
        raise InvalidReviewError(f"Review is too short (minimum {MIN_REVIEW_CHARS} characters).")
    if len(cleaned) > MAX_REVIEW_CHARS:
        raise InvalidReviewError(f"Review is too long (maximum {MAX_REVIEW_CHARS} characters).")
    if not any(ch.isalpha() for ch in cleaned):
        raise InvalidReviewError("Review must contain some letters, not only numbers or symbols.")
    return cleaned


def resolve_backend(requested: str):
    """Decide which backend will really be used. Returns (backend_used, warnings)."""
    if requested not in SENTIMENT_BACKENDS:
        return "vader", [f"Requested backend '{requested}' is not available; used VADER instead."]
    if requested == "distilbert":
        try:
            distilbert_backend.ensure_loaded()
        except BackendUnavailable as exc:
            return "vader", [f"{exc} Used VADER instead."]
    return requested, []


def analyze_review(text: str, backend: str = "vader") -> dict:
    review = validate_review(text)
    used, warnings = resolve_backend(backend)
    sentiment = SENTIMENT_BACKENDS[used](review)

    letters = [ch for ch in review if ch.isalpha()]
    if letters and sum(1 for ch in letters if ord(ch) > 127) / len(letters) > 0.3:
        warnings.append("This text looks non-English; these backends support English only, so treat the result with caution.")

    return {
        "review": review,
        "sentiment": sentiment,
        "key_phrases": yake_keyphrases(review),
        "complaint_categories": detect_complaint_categories(review, sentiment["label"]),
        "backend_requested": backend,
        "backend_used": used,
        "backends": {
            "sentiment": sentiment["backend"],
            "key_phrases": YAKE_LABEL,
            "categories": CATEGORY_METHOD_LABEL,
        },
        "warnings": warnings,
        "limitations": limitations_for(used),
    }


# Which sentiment classes each backend can produce (used by the dashboard).
BACKEND_CLASSES = {
    "vader": ["Positive", "Neutral", "Negative"],
    "distilbert": ["Positive", "Negative"],
}
