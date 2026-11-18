"""Terminal test for V2 data layer: CSV validation, batch analysis and KPIs."""
import json

from data_loader import CSVValidationError, load_feedback_csv
from kpis import compute_kpis
from pipeline import analyze_dataframe

SAMPLE = "data/sample_feedback.csv"


def section(title):
    print()
    print("=" * 8, title, "=" * 8)


section("1. Load and validate the sample CSV")
df, report = load_feedback_csv(SAMPLE)
print("Shape:", df.shape, "| columns:", list(df.columns))
print("Report:", {k: v for k, v in report.items() if k != "warnings"})
print("Warnings:", report["warnings"] or "none")

section("2. Batch analysis (backend: vader)")
out = analyze_dataframe(df, backend="vader")
res = out["results"]
print("Analysed rows:", len(res), "| skipped:", out["skipped"])
print("Backend requested/used:", out["backend_requested"], "/", out["backend_used"])
print("Output columns:", list(res.columns))
print(res[["customer_id", "product", "sentiment", "sentiment_score", "complaint_categories"]].head(6).to_string(index=False))

section("3. KPIs")
k = compute_kpis(res, out["backend_used"], out["backends"])
print("Total:", k["total_reviews"], "| counts:", k["counts"], "| pct:", k["percentages"])
print("Average score:", k["avg_sentiment_score"], "| net sentiment:", k["net_sentiment"])
print("Best / worst product:", k["best_product"], "/", k["worst_product"])
print("Flagged complaint reviews:", k["complaint_reviews_flagged"],
      "| complaints inside non-negative reviews:", k["complaints_in_non_negative_reviews"])
print()
print("Product table:")
for p in k["products"]:
    print(f"  {p['product']:<11} n={p['total']:<2} +{p['positive']} ={p['neutral']} -{p['negative']}  "
          f"neg%={p['negative_pct']:<5} avg={p['avg_score']:+.3f}  top complaint: {p['top_complaint']}")
print("Top complaint categories:", [(c["category"], c["count"]) for c in k["top_complaint_categories"][:5]])
print("Top key phrases:", [(c["phrase"], c["count"]) for c in k["top_key_phrases"][:5]])

checks = {
    "counts add up to total": sum(k["counts"].values()) == k["total_reviews"],
    "product totals add up": sum(p["total"] for p in k["products"]) == k["total_reviews"],
    "percentages near 100": abs(sum(k["percentages"].values()) - 100) < 0.3,
}
try:
    json.dumps(k)
    checks["KPIs are JSON-safe (Chart.js ready)"] = True
except TypeError:
    checks["KPIs are JSON-safe (Chart.js ready)"] = False
print()
for name, ok in checks.items():
    print("PASS" if ok else "FAIL", "-", name)

section("4. Bad and unusual CSV files")
HDR = "customer_id,product,feedback\n"
cases = {
    "empty file": b"",
    "header only": HDR.encode(),
    "missing column": b"id,product,feedback\n1,Laptop,Good\n",
    "Excel file renamed": b"PK\x03\x04\x00\x00binary",
    "too many rows (limit 5)": (HDR + "".join(f"C{i},Laptop,Good item\n" for i in range(8))).encode(),
    "all feedback blank": (HDR + "C1,Laptop,\nC2,Mobile,   \n").encode(),
}
for name, raw in cases.items():
    try:
        load_feedback_csv(raw, max_rows=5)
        print("UNEXPECTED: accepted ->", name)
    except CSVValidationError as exc:
        print(f"Rejected ({name}): {exc}")

section("5. Messy but usable CSV files")
messy = (
    "\ufeffCustomer ID; Product ;FEEDBACK\n"
    "C1;laptop;Great battery life\n"
    "C1;Laptop;  Screen   is   dim \n"
    ";Mobile;Love the camera\n"
    "C4;;Slow delivery\n"
    "C5;Mobile;\n"
).encode("utf-8")
df2, rep2 = load_feedback_csv(messy)
print(df2.to_string(index=False))
for w in rep2["warnings"]:
    print("Warning:", w)

extra = (HDR.strip() + ",region\nC1,Laptop,Good,North\n").encode()
_, rep3 = load_feedback_csv(extra)
print("Extra column ->", rep3["warnings"])

section("6. Rows the analyser must skip, not crash on")
tricky = (HDR + "C1,Laptop,12345 !!!\nC2,Laptop," + "x" * 1001 + "\nC3,Laptop,Works perfectly\n").encode()
df4, _ = load_feedback_csv(tricky)
out4 = analyze_dataframe(df4)
print("Analysed:", len(out4["results"]), "| skipped:", out4["skipped"])
