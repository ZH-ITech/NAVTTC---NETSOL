"""Run the single-review analysis over every row of a feedback DataFrame."""
import logging

import pandas as pd

from analysis import InvalidReviewError, analyze_review, limitations_for, resolve_backend

log = logging.getLogger("feedback-pipeline")

# Same output schema for every sentiment backend.
OUTPUT_COLUMNS = [
    "customer_id", "product", "feedback", "sentiment", "sentiment_score",
    "key_phrases", "complaint_categories", "backend_used",
]


def analyze_dataframe(df: pd.DataFrame, backend: str = "vader") -> dict:
    # Decide the backend ONCE so a whole dataset is never a mix of two backends.
    used, warnings = resolve_backend(backend)
    warnings = set(warnings)
    records, skipped, labels = [], [], None

    for row in df.itertuples(index=False):
        try:
            r = analyze_review(row.feedback, backend=used)
        except InvalidReviewError as exc:
            skipped.append({"csv_row": int(row.csv_row), "reason": str(exc)})
            continue
        except Exception:
            log.exception("Unexpected error on CSV row %s", row.csv_row)
            skipped.append({"csv_row": int(row.csv_row), "reason": "Unexpected analysis error."})
            continue

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
            "backend_used": r["backend_used"],
        })

    return {
        "results": pd.DataFrame(records, columns=OUTPUT_COLUMNS),
        "skipped": skipped,
        "backend_requested": backend,
        "backend_used": used,
        "backends": labels or {},
        "warnings": sorted(warnings),
        "limitations": limitations_for(used),
    }
