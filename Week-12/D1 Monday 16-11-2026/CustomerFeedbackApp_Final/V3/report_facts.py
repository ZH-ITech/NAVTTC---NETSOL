"""Fact sheet for executive reports.

Everything a report may say comes from here. It is aggregated: no customer IDs, no review text.
"""
from analysis import BACKEND_CLASSES, limitations_for

SMALL_SAMPLE = 100


def _count_pct(kpis: dict, label: str):
    return {"count": kpis["counts"][label], "pct": kpis["percentages"][label]}


def build_facts(kpis: dict, backend_used: str, backend_label: str = "") -> dict:
    total = kpis["total_reviews"]
    classes = BACKEND_CLASSES.get(backend_used, ["Positive", "Neutral", "Negative"])
    neutral_supported = "Neutral" in classes

    if backend_used == "distilbert":
        score_note = "Signed model confidence (+ for Positive, - for Negative); usually close to +/-1; not comparable with VADER."
    else:
        score_note = "VADER compound score from -1 (very negative) to +1 (very positive)."

    products = [
        {
            "product": p["product"],
            "reviews": p["total"],
            "positive": p["positive"],
            "neutral": p["neutral"] if neutral_supported else None,
            "negative": p["negative"],
            "negative_pct": p["negative_pct"],
            "avg_score": p["avg_score"],
            "top_complaint": p["top_complaint"],
            "top_complaint_count": p["top_complaint_count"],
        }
        for p in kpis["products"]
    ]

    best = kpis.get("best_product")
    worst = kpis.get("worst_product")

    return {
        "dataset": {
            "reviews_analysed": total,
            "sentiment_backend": backend_label or backend_used,
            "backend_key": backend_used,
            "classes_in_run": kpis["classes_present"],
            "neutral_supported": neutral_supported,
            "sample_size_warning": (
                f"Small sample ({total} reviews): percentages and complaint rankings are unstable."
                if total < SMALL_SAMPLE else None
            ),
        },
        "sentiment": {
            "positive": _count_pct(kpis, "Positive"),
            "neutral": _count_pct(kpis, "Neutral") if neutral_supported else None,
            "negative": _count_pct(kpis, "Negative"),
            "net_sentiment": kpis["net_sentiment"],
            "average_score": kpis["avg_sentiment_score"],
            "average_score_note": score_note,
        },
        "products": products,
        "best_product": {"product": best["product"], "avg_score": best["avg_score"]} if best else None,
        "weakest_product": {"product": worst["product"], "avg_score": worst["avg_score"]} if worst else None,
        "complaints": {
            "top_categories": kpis["top_complaint_categories"][:5],
            "reviews_with_complaint_flag": kpis["complaint_reviews_flagged"],
            "complaints_inside_non_negative_reviews": kpis["complaints_in_non_negative_reviews"],
        },
        "negative_review_phrases": kpis["top_negative_key_phrases"][:8],
        "limitations": limitations_for(backend_used),
    }


def allowed_numbers(facts: dict) -> set:
    """Every number that may legitimately appear in a report (absolute values)."""
    found = set()

    def walk(node):
        if isinstance(node, bool):
            return
        if isinstance(node, (int, float)):
            value = abs(float(node))
            found.add(round(value, 3))
            found.add(round(value, 1))
            found.add(float(round(value)))
        elif isinstance(node, dict):
            for item in node.values():
                walk(item)
        elif isinstance(node, (list, tuple)):
            for item in node:
                walk(item)

    walk(facts)
    return found
