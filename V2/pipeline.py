"""Run the V1 single-review analysis over every row of a feedback DataFrame."""
import logging

import pandas as pd

from analysis import LIMITATIONS, SENTIMENT_BACKENDS, InvalidReviewError, analyze_review

log = logging.getLogger("feedback-pipeline")

# Same output schema for every sentiment backend.
OUTPUT_COLUMNS = [
    "customer_id", "product", "feedback", "sentiment", "sentiment_score",
    "key_phrases", "complaint_categories", "backend_used",
]


def analyze_dataframe(df: pd.DataFrame, backend: str = "vader") -> dict:
    records, skipped, warnings = [], [], set()
    labels, used = None, None

    for row in df.itertuples(index=False):
        try:
            r = analyze_review(row.feedback, backend=backend)
        except InvalidReviewError as exc:
            skipped.append({"csv_row": int(row.csv_row), "reason": str(exc)})
            continue
        except Exception:
            log.exception("Unexpected error on CSV row %s", row.csv_row)
            skipped.append({"csv_row": int(row.csv_row), "reason": "Unexpected analysis error."})
            continue

        used = r["backend_used"]
        labels = labels or r["backends"]
        warnings.update(r["warnings"])
        records.append({
            "customer_id": row.customer_id,
            "product": row.product,
            "feedback": r["review"],
            "sentiment": r["sentiment"]["label"],
            "sentiment_score": float(r["sentiment"]["score"]),
            "key_phrases": "; ".join(r["key_phrases"]),
            "complaint_categories": "; ".join(r["complaint_categories"]),
            "backend_used": used,
        })

    return {
        "results": pd.DataFrame(records, columns=OUTPUT_COLUMNS),
        "skipped": skipped,
        "backend_requested": backend,
        "backend_used": used or (backend if backend in SENTIMENT_BACKENDS else "vader"),
        "backends": labels or {},
        "warnings": sorted(warnings),
        "limitations": LIMITATIONS,
    }
