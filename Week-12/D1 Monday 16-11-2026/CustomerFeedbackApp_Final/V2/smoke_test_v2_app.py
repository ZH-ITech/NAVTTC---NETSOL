"""Route-level test for the V2 Flask app using Flask's built-in test client (no browser needed)."""
import io
import json
import re

from app import MAX_UPLOAD_MB, app

app.testing = True
client = app.test_client()
results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS" if ok else "FAIL"), "-", name, extra)


def upload(csv_bytes, filename="reviews.csv", backend="vader", **kw):
    return client.post(
        "/analyze",
        data={"file": (io.BytesIO(csv_bytes), filename), "backend": backend},
        content_type="multipart/form-data",
        **kw,
    )


HDR = b"customer_id,product,feedback\n"

# --- basic pages ---
r = client.get("/")
check("GET / loads the upload page", r.status_code == 200 and b"Analyse CSV" in r.data)
r = client.get("/health")
check("GET /health reports V2", r.status_code == 200 and r.get_json()["version"] == "V2", str(r.get_json()))

# --- sample CSV -> results page ---
r = client.post("/analyze", data={"use_sample": "1", "backend": "vader"})
check("Sample CSV redirects to a results page", r.status_code == 303 and "/results/" in r.headers["Location"])
loc = r.headers["Location"]
token = loc.rsplit("/", 1)[-1]
page = client.get(loc)
html = page.get_data(as_text=True)
check("Results page loads", page.status_code == 200)
check("Backend label is shown", "Backend actually used: vader" in html)
check("KPI and product sections are present", "Reviews analysed" in html and "Product analytics" in html)
m = re.search(r'<script id="chart-data" type="application/json">(.*?)</script>', html, re.S)
chart = json.loads(m.group(1)) if m else {}
check("Chart data is valid JSON with 4 charts", set(chart) == {"sentiment", "products", "avg_scores", "categories"}, str(sorted(chart)))
check("Chart.js is referenced", "chart.umd.min.js" in html)

# --- download ---
d = client.get(f"/download/{token}")
text = d.data.decode("utf-8-sig")
lines = text.strip().splitlines()
check("Download is a CSV attachment", d.status_code == 200 and d.mimetype == "text/csv"
      and "attachment" in d.headers["Content-Disposition"])
check("Download has header + 20 rows", len(lines) == 21, f"({len(lines)} lines)")
check("Download keeps the schema + result columns",
      lines[0].startswith("customer_id,product,feedback,sentiment,sentiment_score"), lines[0][:70])

# --- upload, filename and unavailable backend ---
sample_rows = HDR + b"C1,Laptop,Great battery life\nC2,Mobile,The screen is dim\n"
r = upload(sample_rows, "my reviews.csv", follow_redirects=True)
check("Upload works and filename is sanitised", r.status_code == 200 and b"my_reviews.csv" in r.data)
r = upload(sample_rows, backend="azure", follow_redirects=True)
h = r.get_data(as_text=True)
check("Unavailable backend falls back and says so",
      "Backend actually used: vader" in h and "requested: azure" in h and "not available" in h)

# --- security: HTML escaping and spreadsheet-formula protection ---
evil = HDR + b'C1,Laptop,"<script>alert(1)</script> bad product"\nC2,Mobile,=1+1 formula test\n'
r = upload(evil, follow_redirects=True)
h = r.get_data(as_text=True)
check("HTML in feedback is escaped, not executed",
      "<script>alert(1)</script>" not in h and "&lt;script&gt;alert(1)&lt;/script&gt;" in h)
tok = re.search(r"/download/([0-9a-f]{32})", h).group(1)
dl = client.get(f"/download/{tok}").data.decode("utf-8-sig")
check("Download neutralises a leading '=' (formula injection)", "'=1+1 formula test" in dl)

# --- error handling ---
r = client.post("/analyze", data={"backend": "vader"})
check("No file -> friendly 400", r.status_code == 400 and b"choose a CSV file" in r.data)
r = upload(sample_rows, "notes.xlsx")
check("Wrong extension -> 400", r.status_code == 400 and b"Only .csv files" in r.data)
r = upload(b"PK\x03\x04binary", "fake.csv")
check("Renamed Excel file -> 400", r.status_code == 400 and b"does not look like a text CSV" in r.data)
r = upload(b"id,product,feedback\n1,Laptop,Good\n")
check("Missing column -> 400", r.status_code == 400 and b"Missing required column" in r.data)
r = upload(HDR)
check("Header only -> 400", r.status_code == 400 and b"no data rows" in r.data)
r = client.get("/results/" + "0" * 32)
check("Unknown result token -> 404 with message", r.status_code == 404 and b"no longer available" in r.data)
r = client.get("/results/not-a-token")
check("Malformed token -> 404", r.status_code == 404)
big = HDR + b"C1,Laptop,Good\n" * ((MAX_UPLOAD_MB * 1024 * 1024) // 15 + 1000)
r = upload(big)
check("File over the size limit -> 413", r.status_code == 413 and b"too large" in r.data)

# --- single review (V1 feature kept) ---
r = client.post("/single", data={"review": "The battery drains very quickly.", "backend": "vader"})
check("Single review still works", r.status_code == 200 and b"Backend actually used" in r.data)
r = client.post("/single", data={"review": "12345 !!!", "backend": "vader"})
check("Single review validation message", b"must contain some letters" in r.data)

print()
print(f"{sum(results)} of {len(results)} checks passed")

