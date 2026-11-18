"""Local NLP backends: VADER (sentiment) and YAKE (key phrases)."""
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import yake

VADER_LABEL = "VADER (local, rule-based lexicon, English only)"
YAKE_LABEL = "YAKE (local, statistical, unsupervised)"

# Standard VADER cut-offs on the compound score (-1 to +1).
POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05

_vader = SentimentIntensityAnalyzer()
_yake = yake.KeywordExtractor(lan="en", n=2, dedupLim=0.7, top=8)


def vader_sentiment(text: str) -> dict:
    """Return the shared sentiment schema used by every backend."""
    scores = _vader.polarity_scores(text)
    compound = float(scores["compound"])
    if compound >= POSITIVE_THRESHOLD:
        label = "Positive"
    elif compound <= NEGATIVE_THRESHOLD:
        label = "Negative"
    else:
        label = "Neutral"
    return {
        "label": label,
        "score": round(compound, 4),
        "positive": round(float(scores["pos"]), 3),
        "neutral": round(float(scores["neu"]), 3),
        "negative": round(float(scores["neg"]), 3),
        "backend": VADER_LABEL,
    }


def yake_keyphrases(text: str, top: int = 5) -> list:
    """Return up to `top` key phrases as plain lowercase strings."""
    try:
        raw = _yake.extract_keywords(text)
    except Exception:
        return []
    phrases = []
    # In YAKE a LOWER score means a MORE relevant phrase.
    for phrase, _score in sorted(raw, key=lambda item: float(item[1])):
        cleaned = phrase.strip().lower()
        if cleaned and cleaned not in phrases:
            phrases.append(cleaned)
    return phrases[:top]
