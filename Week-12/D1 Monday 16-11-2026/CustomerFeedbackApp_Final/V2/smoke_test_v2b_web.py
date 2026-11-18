"""Web-level test for V2b: DistilBERT option, backend labels, binary-model notes and the comparison page."""
import io
import json
import re

import distilbert_backend
from app import app

app.testing = True
client = app.test_client()
results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS" if ok else "FAIL"), "-", name, extra)


def post_csv(raw, backend):
    return client.post(
        "/analyze",
        data={"file": (io.BytesIO(raw), "reviews.csv"), "backend": backend},
        content_type="multipart/form-data",
    )


def token_of(response):
    return response.headers["Location"].rsplit("/", 1)[-1]


# --- dropdown ---
page = client.get("/").get_data(as_text=True)
check("DistilBERT option is enabled", re.search(r'<option value="distilbert"\s*>', page) is not None)
check("Azure option stays disabled", re.search(r'<option value="azure"\s+disabled', page) is not None)
check("First-use loading hint is shown", "first use loads the model" in page)

# --- VADER run keeps its normal look ---
r = client.post("/analyze", data={"use_sample": "1", "backend": "vader"})
vader_token = token_of(r)
html = client.get(f"/results/{vader_token}").get_data(as_text=True)
check("VADER page: backend label", "Backend actually used: vader" in html)
check("VADER page: Neutral count shown", "n/a" not in html.split("Neutral</div>")[1][:120])
check("VADER page: singular wording ('1 review', not '1 reviews')", re.search(r"(?<![0-9])1 reviews", html) is None)
check("VADER page: no binary-model alert", "binary model" not in html)
check("VADER page: Compare button present", f"/compare/{vader_token}" in html)

# --- DistilBERT run ---
r = client.post("/analyze", data={"use_sample": "1", "backend": "distilbert"})
bert_token = token_of(r)
html = client.get(f"/results/{bert_token}").get_data(as_text=True)
check("DistilBERT page: backend label", "Backend actually used: distilbert" in html)
check("DistilBERT page: Neutral shown as n/a", "not produced by this backend" in html)
check("DistilBERT page: binary-model alert", "binary model" in html)
check("DistilBERT page: limitation lists the missing Neutral class", "no Neutral class" in html)
check("DistilBERT page: score-scale note", "scale depends on the backend" in html)
dl = client.get(f"/download/{bert_token}").data.decode("utf-8-sig").splitlines()
vdl = client.get(f"/download/{vader_token}").data.decode("utf-8-sig").splitlines()
check("Download: same columns for both backends", dl[0] == vdl[0] and len(dl) == len(vdl) == 21)
check("Download: backend_used column says distilbert", all(line.rstrip().endswith("distilbert") for line in dl[1:]))

# --- single review ---
r = client.post("/single", data={"review": "The battery drains very quickly.", "backend": "distilbert"})
check("Single review can use DistilBERT", b"Backend actually used: <strong>distilbert</strong>" in r.data)

# --- comparison page ---
r = client.get(f"/compare/{vader_token}")
html = r.get_data(as_text=True)
check("Compare page loads", r.status_code == 200)
check("Compare page names both backends", "VADER (local" in html and "DistilBERT SST-2" in html)
check("Compare page says agreement, not accuracy", "agreement</strong> between two backends" in html)
check("Compare page lists the battery review under VADER Neutral", "The battery drains very quickly." in html)
m = re.search(r'<script id="chart-data" type="application/json">(.*?)</script>', html, re.S)
chart = json.loads(m.group(1)) if m else {}
check("Compare chart data is valid", set(chart) == {"products", "vader_negative_pct", "distilbert_negative_pct"})
m2 = re.search(r"DistilBERT agreed on <strong>(\d+)</strong> \(([\d.]+)%\) and disagreed on <strong>(\d+)</strong>", html)
m3 = re.search(r"VADER gave Positive or Negative: <strong>(\d+)</strong>", html)
if m2 and m3:
    agree, _pct, disagree = int(m2.group(1)), m2.group(2), int(m2.group(3))
    check("Agreement numbers add up", agree + disagree == int(m3.group(1)), f"({agree} + {disagree} = {m3.group(1)})")
else:
    check("Agreement numbers add up", False)

r = client.get("/compare/" + "0" * 32)
check("Compare: unknown token -> 404", r.status_code == 404)

# --- repeated customer IDs must not multiply rows ---
dup = (b"customer_id,product,feedback\nC1,Laptop,The battery drains very quickly.\n"
       b"C1,Laptop,The battery drains very quickly.\nC1,Mobile,Great screen and camera.\n")
t = token_of(post_csv(dup, "vader"))
html = client.get(f"/compare/{t}").get_data(as_text=True)
check("Repeated IDs: exactly 3 rows compared", "same 3 reviews" in html)

# --- fallback when DistilBERT cannot load ---
saved = distilbert_backend._classifier, distilbert_backend._load_error
distilbert_backend._classifier = None
distilbert_backend._load_error = "DistilBERT could not be loaded (SimulatedError)."
r = post_csv(dup, "distilbert")
html = client.get(f"/results/{token_of(r)}").get_data(as_text=True)
check("Fallback page: says vader was used", "Backend actually used: vader" in html and "requested: distilbert" in html)
check("Fallback page: explains why", "Used VADER instead" in html)
fresh = token_of(post_csv(dup, "vader"))
r = client.get(f"/compare/{fresh}")
check("Compare refuses politely when DistilBERT cannot load", r.status_code == 400 and b"could not be used" in r.data)
distilbert_backend._classifier, distilbert_backend._load_error = saved

print()
print(f"{sum(results)} of {len(results)} checks passed")
