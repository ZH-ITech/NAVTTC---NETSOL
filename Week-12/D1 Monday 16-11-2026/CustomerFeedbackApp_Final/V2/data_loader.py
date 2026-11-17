"""Read and validate an uploaded customer-feedback CSV.

Required schema (same for every backend): customer_id, product, feedback.
"""
import io
from pathlib import Path

import pandas as pd

from config import MAX_ROWS

REQUIRED_COLUMNS = ["customer_id", "product", "feedback"]


class CSVValidationError(ValueError):
    """Raised with a student-friendly message when the CSV cannot be used."""


def _read_bytes(source) -> bytes:
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    if hasattr(source, "read"):
        data = source.read()
        return data if isinstance(data, bytes) else str(data).encode("utf-8")
    try:
        return Path(source).read_bytes()
    except FileNotFoundError:
        raise CSVValidationError("CSV file not found.") from None


def _decode(raw: bytes):
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise CSVValidationError(
        "Could not read the text encoding of this file. Save it as 'CSV UTF-8' and try again."
    )


def _normalise_header(name) -> str:
    return str(name).strip().lower().replace(" ", "_").replace("-", "_")


def _parse(text: str, sep: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(
            io.StringIO(text), sep=sep, dtype=str, keep_default_na=False, skip_blank_lines=True
        )
    except pd.errors.EmptyDataError:
        raise CSVValidationError("The file is empty.") from None
    except pd.errors.ParserError as exc:
        first_line = str(exc).splitlines()[0]
        raise CSVValidationError(f"The file is not a valid CSV: {first_line}") from None
    df.columns = [_normalise_header(c) for c in df.columns]
    return df


def load_feedback_csv(source, max_rows=None):
    """Return (DataFrame, report). Raises CSVValidationError for unusable files.

    DataFrame columns: csv_row, customer_id, product, feedback.
    """
    max_rows = MAX_ROWS if max_rows is None else max_rows
    raw = _read_bytes(source)

    if not raw.strip():
        raise CSVValidationError("The file is empty.")
    if raw[:2] == b"PK" or b"\x00" in raw:
        raise CSVValidationError(
            "This does not look like a text CSV file (an Excel .xlsx file renamed to .csv?). "
            "Use 'Save As > CSV UTF-8' in Excel."
        )

    text, encoding = _decode(raw)
    df = _parse(text, ",")
    if not set(REQUIRED_COLUMNS).issubset(df.columns) and len(df.columns) == 1 and ";" in df.columns[0]:
        df = _parse(text, ";")

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise CSVValidationError(
            f"Missing required column(s): {', '.join(missing)}. "
            f"Found: {', '.join(df.columns)}. Expected: customer_id, product, feedback."
        )

    warnings = []
    extra = [c for c in df.columns if c not in REQUIRED_COLUMNS]
    if extra:
        warnings.append(f"Ignored extra column(s): {', '.join(extra)}.")

    df = df[REQUIRED_COLUMNS].copy()
    rows_read = len(df)
    if rows_read == 0:
        raise CSVValidationError("The file has a header row but no data rows.")
    if rows_read > max_rows:
        raise CSVValidationError(
            f"The file has {rows_read} data rows; the limit is {max_rows}. Split the file or raise MAX_ROWS in .env."
        )

    df.insert(0, "csv_row", range(2, rows_read + 2))  # row 1 is the header

    for col in REQUIRED_COLUMNS:
        df[col] = df[col].str.replace(r"\s+", " ", regex=True).str.strip()

    empty_feedback = df["feedback"] == ""
    dropped_empty = int(empty_feedback.sum())
    df = df[~empty_feedback].reset_index(drop=True)
    if dropped_empty:
        warnings.append(f"Dropped {dropped_empty} row(s) with empty feedback.")
    if df.empty:
        raise CSVValidationError("Every row has empty feedback text, so there is nothing to analyse.")

    blank_product = df["product"] == ""
    blank_product_n = int(blank_product.sum())
    if blank_product_n:
        df.loc[blank_product, "product"] = "Unknown"
        warnings.append(f"{blank_product_n} row(s) had no product and were labelled 'Unknown'.")

    spellings = {}
    before = df["product"].nunique()
    df["product"] = df["product"].map(lambda p: spellings.setdefault(p.lower(), p))
    if df["product"].nunique() < before:
        warnings.append("Product names that differed only by upper/lower case were merged.")

    blank_id = df["customer_id"] == ""
    blank_id_n = int(blank_id.sum())
    if blank_id_n:
        df.loc[blank_id, "customer_id"] = "ROW" + df.loc[blank_id, "csv_row"].astype(str)
        warnings.append(f"{blank_id_n} row(s) had no customer_id; temporary IDs were created.")

    dup_n = int(df["customer_id"].duplicated().sum())
    if dup_n:
        warnings.append(f"{dup_n} repeated customer_id value(s) found (rows were kept).")

    report = {
        "encoding": encoding,
        "rows_read": rows_read,
        "rows_kept": len(df),
        "rows_dropped_empty_feedback": dropped_empty,
        "products": sorted(df["product"].unique().tolist()),
        "warnings": warnings,
    }
    return df, report
