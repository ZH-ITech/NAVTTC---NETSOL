"""Single-review analysis pipeline. Reused unchanged by later versions."""
from categories import CATEGORY_METHOD_LABEL, detect_complaint_categories
from config import MAX_REVIEW_CHARS, MIN_REVIEW_CHARS
from nlp_backends import YAKE_LABEL, vader_sentiment, yake_keyphrases

# Add "distilbert" and "azure" here in later versions.
SENTIMENT_BACKENDS = {"vader": vader_sentiment}

LIMITATIONS = [
    "VADER is an English lexicon tool: it can miss sarcasm, negation and domain wording "
    "(for example 'stopped working' may score Neutral).",
    "Complaint categories come from keyword rules: they can miss unusual wording, "
    "mis-handle negation, and over-assign categories when sentiment is Negative.",
]


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


def analyze_review(text: str, backend: str = "vader") -> dict:
    review = validate_review(text)
    warnings = []

    used = backend
    if backend not in SENTIMENT_BACKENDS:
        used = "vader"
        warnings.append(f"Requested backend '{backend}' is not available; used VADER instead.")

    sentiment = SENTIMENT_BACKENDS[used](review)

    letters = [ch for ch in review if ch.isalpha()]
    if letters and sum(1 for ch in letters if ord(ch) > 127) / len(letters) > 0.3:
        warnings.append("This text looks non-English; VADER supports English only, so treat the result with caution.")

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
        "limitations": LIMITATIONS,
    }
