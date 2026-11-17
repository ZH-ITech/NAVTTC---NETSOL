"""Business KPIs. Pure Python/pandas maths: identical for every sentiment backend."""
from collections import Counter

import pandas as pd

LABELS = ["Positive", "Neutral", "Negative"]


def _split(cell) -> list:
    return [p.strip() for p in str(cell).split(";") if p.strip()]


def _pct(part: int, total: int) -> float:
    return round(100.0 * part / total, 1) if total else 0.0


def _label_counts(frame: pd.DataFrame) -> dict:
    return {label: int((frame["sentiment"] == label).sum()) for label in LABELS}


def compute_kpis(df: pd.DataFrame, backend_used: str, backends: dict = None, top_n: int = 10) -> dict:
    total = len(df)
    counts = _label_counts(df)

    products = []
    for product, g in df.groupby("product", sort=True):
        n = len(g)
        c = _label_counts(g)
        cats = Counter(cat for cell in g["complaint_categories"] for cat in _split(cell))
        top = cats.most_common(1)
        products.append({
            "product": str(product),
            "total": n,
            "positive": c["Positive"], "neutral": c["Neutral"], "negative": c["Negative"],
            "positive_pct": _pct(c["Positive"], n),
            "neutral_pct": _pct(c["Neutral"], n),
            "negative_pct": _pct(c["Negative"], n),
            "avg_score": round(float(g["sentiment_score"].mean()), 3),
            "top_complaint": top[0][0] if top else None,
            "top_complaint_count": int(top[0][1]) if top else 0,
        })
    products.sort(key=lambda p: (-p["total"], p["product"]))

    best = worst = None
    if len(products) >= 2:
        hi = max(products, key=lambda p: p["avg_score"])
        lo = min(products, key=lambda p: p["avg_score"])
        best = {"product": hi["product"], "avg_score": hi["avg_score"]}
        worst = {"product": lo["product"], "avg_score": lo["avg_score"]}

    cat_counter, phrase_counter, neg_phrase_counter = Counter(), Counter(), Counter()
    flagged = hidden = 0
    for cats, phrases, label in zip(df["complaint_categories"], df["key_phrases"], df["sentiment"]):
        cat_list, phrase_list = _split(cats), _split(phrases)
        if cat_list:
            flagged += 1
            if label != "Negative":
                hidden += 1
        cat_counter.update(set(cat_list))
        phrase_counter.update(set(phrase_list))
        if label == "Negative":
            neg_phrase_counter.update(set(phrase_list))

    return {
        "total_reviews": total,
        "counts": counts,
        "percentages": {label: _pct(counts[label], total) for label in LABELS},
        "avg_sentiment_score": round(float(df["sentiment_score"].mean()), 3) if total else 0.0,
        "net_sentiment": round(_pct(counts["Positive"], total) - _pct(counts["Negative"], total), 1),
        "products": products,
        "best_product": best,
        "worst_product": worst,
        "complaint_reviews_flagged": flagged,
        "complaints_in_non_negative_reviews": hidden,
        "top_complaint_categories": [
            {"category": k, "count": int(v), "pct_of_reviews": _pct(v, total)}
            for k, v in cat_counter.most_common(top_n)
        ],
        "top_key_phrases": [{"phrase": k, "count": int(v)} for k, v in phrase_counter.most_common(top_n)],
        "top_negative_key_phrases": [
            {"phrase": k, "count": int(v)} for k, v in neg_phrase_counter.most_common(top_n)
        ],
        "backend_used": backend_used,
        "backends": backends or {},
        "classes_present": [label for label in LABELS if counts[label] > 0],
    }
