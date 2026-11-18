"""Route-level tests for the V3 Executive Report feature."""
import re

from app import app

app.testing = True
client = app.test_client()
results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS" if ok else "FAIL"), "-", name, extra)


# Generate a real analysis using the bundled sample dataset.
response = client.post(
    "/analyze",
    data={"use_sample": "1", "backend": "vader"},
)

check(
    "Sample analysis creates a results page",
    response.status_code == 303 and "/results/" in response.headers.get("Location", ""),
)

if response.status_code != 303:
    print("\nCannot continue: sample analysis did not create a result.")
    raise SystemExit(1)

results_url = response.headers["Location"]
token_match = re.search(r"/results/([0-9a-f]{32})$", results_url)
token = token_match.group(1) if token_match else None

check("Analysis token is valid", token is not None)

if token is None:
    raise SystemExit(1)

# Results page should expose the new feature.
dashboard = client.get(results_url)
dashboard_html = dashboard.get_data(as_text=True)

check(
    "Results dashboard loads",
    dashboard.status_code == 200,
)
check(
    "Dashboard contains Executive Report link",
    "Executive Report" in dashboard_html and f"/report/{token}" in dashboard_html,
)

# Template-based report must work without an API key.
report_response = client.get(f"/report/{token}?backend=template")
report_html = report_response.get_data(as_text=True)

check(
    "Template-based executive report loads",
    report_response.status_code == 200,
)
check(
    "Executive report sections render",
    all(section in report_html for section in (
        "Executive Feedback Intelligence Report",
        "Executive headline",
        "Key findings",
        "Complaint analysis",
        "Recommendations",
        "Calculated sentiment snapshot",
        "Caveats and limitations",
        "Numerical validation",
    )),
)
check(
    "Report identifies template-based generation",
    "Template-based report" in report_html,
)

# Automatic mode should safely fall back when OpenAI is not configured.
auto_response = client.get(f"/report/{token}?backend=auto")
check(
    "Automatic mode renders a report",
    auto_response.status_code == 200,
)

# Markdown download.
download = client.get(f"/report/{token}/download?backend=template")
markdown = download.get_data(as_text=True)

check(
    "Markdown report downloads as an attachment",
    download.status_code == 200
    and download.mimetype == "text/markdown"
    and "attachment" in download.headers.get("Content-Disposition", ""),
)
check(
    "Markdown contains report sections",
    "# Customer Feedback Intelligence" in markdown
    and "## Executive Report" in markdown
    and "## Numerical validation" in markdown,
)
check(
    "Markdown excludes raw review text and customer IDs",
    "customer_id" not in markdown.lower()
    and "customer feedback" in markdown.lower(),
)

# Invalid and expired tokens.
missing = client.get("/report/" + "0" * 32)
check(
    "Unknown report token returns 404",
    missing.status_code == 404,
)

malformed = client.get("/report/not-a-token")
check(
    "Malformed report token returns 404",
    malformed.status_code == 404,
)

print()
print(f"{sum(results)} of {len(results)} checks passed")

if not all(results):
    raise SystemExit(1)
