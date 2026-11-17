"""V1 Flask app: analyse one customer review with the local backend."""
import logging

from flask import Flask, jsonify, render_template, request

from analysis import SENTIMENT_BACKENDS, InvalidReviewError, analyze_review
from config import FLASK_DEBUG, MAX_REVIEW_CHARS, MAX_UPLOAD_MB

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("feedback-v1")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

# (key, label, version that enables it)
BACKEND_CHOICES = [
    ("vader", "VADER (local, low-spec)", "V1"),
    ("distilbert", "DistilBERT (local, English positive/negative)", "V2"),
    ("azure", "Azure AI Language (needs valid access)", "V3"),
]


def base_context() -> dict:
    return {
        "choices": [
            {"key": k, "label": label, "available": k in SENTIMENT_BACKENDS, "version": ver}
            for k, label, ver in BACKEND_CHOICES
        ],
        "max_chars": MAX_REVIEW_CHARS,
        "review_text": "",
        "selected_backend": "vader",
        "result": None,
        "error": None,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    ctx = base_context()
    if request.method == "POST":
        review_text = request.form.get("review", "")
        backend = request.form.get("backend", "vader")
        ctx["review_text"] = review_text[: MAX_REVIEW_CHARS + 50]
        ctx["selected_backend"] = backend
        try:
            ctx["result"] = analyze_review(review_text, backend=backend)
        except InvalidReviewError as exc:
            ctx["error"] = str(exc)
        except Exception:
            log.exception("Unexpected error while analysing a review")
            ctx["error"] = "Something went wrong while analysing the review. Please try again."
    return render_template("index.html", **ctx)


@app.route("/health")
def health():
    return jsonify(
        status="ok",
        version="V1",
        sentiment_backends_available=sorted(SENTIMENT_BACKENDS.keys()),
    )


@app.errorhandler(413)
def too_large(_error):
    ctx = base_context()
    ctx["error"] = f"Request too large (limit {MAX_UPLOAD_MB} MB)."
    return render_template("index.html", **ctx), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=FLASK_DEBUG)
