"""Run VADER and DistilBERT on the same rows and compare them.

This measures AGREEMENT between two backends, not accuracy: no human-labelled answers exist.
"""
from kpis import compute_kpis
from pipeline import analyze_dataframe

BACKENDS = ("vader", "distilbert")
MAX_ROWS_SHOWN = 50


class ComparisonUnavailable(RuntimeError):
    """One of the two backends could not be used for the comparison."""


def _with_occurrence(frame):
    # Customer IDs can repeat, so number identical (id, text) rows to keep the join one-to-one.
    frame = frame.copy()
    frame["_n"] = frame.groupby(["customer_id", "feedback"]).cumcount()
    return frame


def _rows(frame):
    return [
        {"customer_id": r.customer_id, "product": r.product, "feedback": r.feedback,
         "vader": r.sentiment_vader, "distilbert": r.sentiment_distilbert}
        for r in frame.head(MAX_ROWS_SHOWN).itertuples()
    ]


def build_comparison(input_df) -> dict:
    runs = {}
    for name in BACKENDS:
        out = analyze_dataframe(input_df, backend=name)
        if out["backend_used"] != name:
            reason = " ".join(out["warnings"]) or "unknown reason"
            raise ComparisonUnavailable(f"{name} could not be used: {reason}")
        if out["results"].empty:
            raise ComparisonUnavailable("None of the rows could be analysed.")
        runs[name] = out

    kpis = {n: compute_kpis(r["results"], r["backend_used"], r["backends"]) for n, r in runs.items()}

    left = _with_occurrence(runs["vader"]["results"])[["customer_id", "product", "feedback", "sentiment", "_n"]]
    right = _with_occurrence(runs["distilbert"]["results"])[["customer_id", "feedback", "sentiment", "_n"]]
    merged = left.merge(right, on=["customer_id", "feedback", "_n"], suffixes=("_vader", "_distilbert"))

    comparable = merged[merged["sentiment_vader"] != "Neutral"]
    disagree = comparable[comparable["sentiment_vader"] != comparable["sentiment_distilbert"]]
    vader_neutral = merged[merged["sentiment_vader"] == "Neutral"]
    agree_n = len(comparable) - len(disagree)

    products = sorted({p["product"] for k in kpis.values() for p in k["products"]})

    def negative_pct(k):
        lookup = {p["product"]: p["negative_pct"] for p in k["products"]}
        return [lookup.get(p, 0.0) for p in products]

    return {
        "kpis": kpis,
        "labels": {n: runs[n]["backends"].get("sentiment", n) for n in runs},
        "limitations": {n: runs[n]["limitations"] for n in runs},
        "agreement": {
            "rows_compared": len(merged),
            "comparable": len(comparable),
            "agree": agree_n,
            "disagree": len(disagree),
            "agree_pct": round(100.0 * agree_n / len(comparable), 1) if len(comparable) else 0.0,
            "vader_neutral": len(vader_neutral),
        },
        "disagreements": _rows(disagree),
        "vader_neutral_rows": _rows(vader_neutral),
        "chart": {
            "products": products,
            "vader_negative_pct": negative_pct(kpis["vader"]),
            "distilbert_negative_pct": negative_pct(kpis["distilbert"]),
        },
    }
