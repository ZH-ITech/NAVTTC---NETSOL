"""V3 Flask app: customer feedback intelligence with executive reporting."""
import logging
import re
import threading
import uuid
from pathlib import Path
from collections import OrderedDict

from flask import Flask, Response, jsonify, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from analysis import BACKEND_CLASSES, SENTIMENT_BACKENDS, InvalidReviewError, analyze_review
from comparison import ComparisonUnavailable, build_comparison
from config import BASE_DIR, FLASK_DEBUG, MAX_REVIEW_CHARS, MAX_ROWS, MAX_UPLOAD_MB, REPORT_BACKEND
from report_facts import build_facts
from report_service import generate_report
from report_markdown import build_markdown_report
from data_loader import CSVValidationError, load_feedback_csv
from kpis import LABELS, compute_kpis
from pipeline import analyze_dataframe

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("feedback-v3")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

SAMPLE_PATH = BASE_DIR / "data" / "sample_feedback.csv"
MAX_TABLE_ROWS = 100
MAX_STORED_RESULTS = 10
TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")

# Results live in memory only (nothing is written to disk) and vanish on restart.
RESULT_STORE = OrderedDict()
STORE_LOCK = threading.Lock()


def backend_choices() -> list:
    return [
        {"key": "vader", "label": "VADER (local, low-spec)",
         "available": "vader" in SENTIMENT_BACKENDS, "version": ""},
        {"key": "distilbert",
         "label": "DistilBERT (local, English, Positive/Negative only; first use loads the model)",
         "available": "distilbert" in SENTIMENT_BACKENDS, "version": "install requirements-distilbert.txt"},
        {"key": "azure", "label": "Azure AI Language (needs valid access)",
         "available": "azure" in SENTIMENT_BACKENDS, "version": "V3"},
    ]


def store_result(payload: dict) -> str:
    token = uuid.uuid4().hex
    with STORE_LOCK:
        RESULT_STORE[token] = payload
        while len(RESULT_STORE) > MAX_STORED_RESULTS:
            RESULT_STORE.popitem(last=False)
    return token


def get_result(token: str):
    if not TOKEN_RE.match(token or ""):
        return None
    with STORE_LOCK:
        return RESULT_STORE.get(token)


def base_context() -> dict:
    return {
        "choices": backend_choices(),
        "max_chars": MAX_REVIEW_CHARS,
        "max_rows": MAX_ROWS,
        "max_mb": MAX_UPLOAD_MB,
        "sample_available": SAMPLE_PATH.exists(),
        "selected_backend": "vader",
        "review_text": "",
        "single_result": None,
        "error": None,
    }


def chart_payload(k: dict) -> dict:
    products = k["products"]
    cats = k["top_complaint_categories"][:8]
    return {
        "sentiment": {"labels": LABELS, "values": [k["counts"][label] for label in LABELS]},
        "products": {
            "labels": [p["product"] for p in products],
            "positive": [p["positive"] for p in products],
            "neutral": [p["neutral"] for p in products],
            "negative": [p["negative"] for p in products],
        },
        "avg_scores": {
            "labels": [p["product"] for p in products],
            "values": [p["avg_score"] for p in products],
        },
        "categories": {
            "labels": [c["category"] for c in cats],
            "values": [c["count"] for c in cats],
        },
    }


def to_safe_csv(df) -> str:
    """CSV text for download. Text cells that start with = + - @ are prefixed with an
    apostrophe so Excel cannot run them as formulas (CSV/formula injection)."""
    safe = df.copy()
    for col in safe.select_dtypes(include=["object", "string"]).columns:
        safe[col] = safe[col].map(
            lambda v: "'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@", "\t", "\r")) else v
        )
    return "\ufeff" + safe.to_csv(index=False)  # BOM so Excel reads UTF-8 correctly


def render_index_error(message: str, backend: str = "vader", status: int = 400):
    ctx = base_context()
    ctx["error"] = message
    ctx["selected_backend"] = backend
    return render_template("index.html", **ctx), status


@app.get("/")
def index():
    return render_template("index.html", **base_context())


@app.post("/analyze")
def analyze_csv():
    backend = request.form.get("backend", "vader")
    try:
        if request.form.get("use_sample") == "1":
            if not SAMPLE_PATH.exists():
                raise CSVValidationError("The bundled sample file was not found in the data folder.")
            source, display_name = SAMPLE_PATH, SAMPLE_PATH.name
        else:
            upload = request.files.get("file")
            if upload is None or not upload.filename:
                raise CSVValidationError("Please choose a CSV file to upload.")
            if not upload.filename.lower().endswith(".csv"):
                raise CSVValidationError("Only .csv files are accepted.")
            source, display_name = upload.stream, secure_filename(upload.filename) or "upload.csv"

        df, report = load_feedback_csv(source)
        out = analyze_dataframe(df, backend=backend)
        if out["results"].empty:
            raise CSVValidationError("None of the rows could be analysed. See the row messages for the reasons.")
        kpis = compute_kpis(out["results"], out["backend_used"], out["backends"])
    except CSVValidationError as exc:
        return render_index_error(str(exc), backend)
    except Exception:
        log.exception("Unexpected error while analysing a CSV")
        return render_index_error("Something went wrong while analysing the file. Please try again.", backend, 500)

    token = store_result({
        "results": out["results"], "kpis": kpis, "report": report, "skipped": out["skipped"],
        "warnings": out["warnings"], "limitations": out["limitations"],
        "backend_requested": out["backend_requested"], "backend_used": out["backend_used"],
        "backends": out["backends"], "source_name": display_name,
        "input": df, "compare": None,
    })
    return redirect(url_for("results", token=token), code=303)


@app.get("/results/<token>")
def results(token):
    data = get_result(token)
    if data is None:
        return render_index_error(
            "That analysis is no longer available (results are kept in memory only). Please upload the file again.",
            status=404,
        )
    frame = data["results"]
    return render_template(
        "results.html",
        token=token, k=data["kpis"], report=data["report"], skipped=data["skipped"],
        warnings=data["warnings"], limitations=data["limitations"],
        backend_requested=data["backend_requested"], backend_used=data["backend_used"],
        backends=data["backends"], source_name=data["source_name"],
        chart_data=chart_payload(data["kpis"]),
        rows=frame.head(MAX_TABLE_ROWS).to_dict("records"),
        row_total=len(frame), max_rows_shown=MAX_TABLE_ROWS,
        neutral_supported="Neutral" in BACKEND_CLASSES.get(data["backend_used"], ["Neutral"]),
        compare_available="distilbert" in SENTIMENT_BACKENDS,
    )




def prepare_executive_report(data: dict, preference: str):
    """Build an aggregated fact sheet and generate a validated executive report."""
    backend_label = data["backends"].get("sentiment", data["backend_used"])
    facts = build_facts(
        data["kpis"],
        data["backend_used"],
        backend_label=backend_label,
    )
    report = generate_report(facts, preference=preference)
    return facts, report


@app.get("/report/<token>")
def executive_report(token):
    data = get_result(token)
    if data is None:
        return render_index_error(
            "That analysis is no longer available. Please upload the file again.",
            status=404,
        )

    preference = (request.args.get("backend") or REPORT_BACKEND).strip().lower()
    if preference not in ("template", "auto", "openai"):
        preference = "auto"

    try:
        facts, report = prepare_executive_report(data, preference)
    except Exception:
        log.exception("Executive report generation failed")
        return render_index_error(
            "The executive report could not be generated. Please try again.",
            status=500,
        )

    return render_template(
        "executive_report.html",
        token=token,
        source_name=data["source_name"],
        facts=facts,
        report=report,
        selected_backend=preference,
    )


@app.get("/report/<token>/download")
def download_executive_report(token):
    data = get_result(token)
    if data is None:
        return render_index_error(
            "That analysis is no longer available. Please upload the file again.",
            status=404,
        )

    preference = (request.args.get("backend") or REPORT_BACKEND).strip().lower()
    if preference not in ("template", "auto", "openai"):
        preference = "auto"

    try:
        facts, report = prepare_executive_report(data, preference)
        markdown = build_markdown_report(
            report,
            facts,
            source_name=data["source_name"],
        )
    except Exception:
        log.exception("Executive report download failed")
        return render_index_error(
            "The executive report download could not be generated.",
            status=500,
        )

    filename = secure_filename(
        Path(data["source_name"]).stem + "_executive_report.md"
    ) or "executive_report.md"

    return Response(
        markdown,
        mimetype="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/compare/<token>")
def compare(token):
    data = get_result(token)
    if data is None:
        return render_index_error("That analysis is no longer available. Please upload the file again.", status=404)
    if "distilbert" not in SENTIMENT_BACKENDS:
        return render_index_error(
            "Comparing backends needs the optional DistilBERT backend. Install requirements-distilbert.txt first.")
    comparison = data.get("compare")
    if comparison is None:
        try:
            comparison = build_comparison(data["input"])
        except ComparisonUnavailable as exc:
            return render_index_error(str(exc))
        except Exception:
            log.exception("Unexpected error while comparing backends")
            return render_index_error("Something went wrong while comparing the backends.", status=500)
        with STORE_LOCK:
            data["compare"] = comparison
    return render_template("compare.html", token=token, cmp=comparison, source_name=data["source_name"])


@app.get("/download/<token>")
def download(token):
    data = get_result(token)
    if data is None:
        return render_index_error("That analysis is no longer available. Please upload the file again.", status=404)
    filename = f"feedback_analysis_{data['backend_used']}.csv"
    return Response(
        to_safe_csv(data["results"]),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/single")
def single_review():
    ctx = base_context()
    review_text = request.form.get("review", "")
    backend = request.form.get("backend", "vader")
    ctx["review_text"] = review_text[: MAX_REVIEW_CHARS + 50]
    ctx["selected_backend"] = backend
    try:
        ctx["single_result"] = analyze_review(review_text, backend=backend)
    except InvalidReviewError as exc:
        ctx["error"] = str(exc)
    except Exception:
        log.exception("Unexpected error while analysing a single review")
        ctx["error"] = "Something went wrong while analysing the review. Please try again."
    return render_template("index.html", **ctx)


@app.get("/health")
def health():
    return jsonify(
        status="ok", version="V3",
        sentiment_backends_available=sorted(SENTIMENT_BACKENDS.keys()),
        stored_results=len(RESULT_STORE),
    )


@app.errorhandler(413)
def too_large(_error):
    return render_index_error(f"The file is too large (limit {MAX_UPLOAD_MB} MB).", status=413)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=FLASK_DEBUG)

