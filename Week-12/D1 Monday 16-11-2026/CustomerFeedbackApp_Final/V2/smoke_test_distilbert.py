"""Terminal test for the optional DistilBERT backend and the VADER fallback."""
import time

import distilbert_backend
from analysis import SENTIMENT_BACKENDS, analyze_review
from data_loader import load_feedback_csv
from kpis import compute_kpis
from pipeline import analyze_dataframe

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS" if ok else "FAIL"), "-", name, extra)


print("Backends registered:", sorted(SENTIMENT_BACKENDS))
check("DistilBERT dependencies detected", distilbert_backend.dependencies_installed())
check("DistilBERT is registered", "distilbert" in SENTIMENT_BACKENDS)

print("\n=== 1. Single reviews: DistilBERT vs VADER ===")
samples = [
    "Excellent laptop, very fast and reliable.",
    "The battery drains very quickly.",
    "Good performance but expensive.",
    "Average product, nothing special.",
    "The product stopped working after two days.",
]
start = time.time()
first = analyze_review(samples[0], backend="distilbert")
print(f"First DistilBERT call (includes model loading): {time.time() - start:.1f} s")
check("Backend actually used is distilbert", first["backend_used"] == "distilbert")
for s in samples:
    d = analyze_review(s, backend="distilbert")
    v = analyze_review(s, backend="vader")
    print(f"  {d['sentiment']['label']:<8} {d['sentiment']['score']:+.3f} | {v['sentiment']['label']:<8} {v['sentiment']['score']:+.3f} | {s}")
d, v = analyze_review(samples[1], "distilbert"), analyze_review(samples[1], "vader")
check("Same result keys for both backends", set(d) == set(v) and set(d["sentiment"]) == set(v["sentiment"]))
check("DistilBERT never returns Neutral", all(
    analyze_review(s, "distilbert")["sentiment"]["label"] in ("Positive", "Negative") for s in samples))
check("Limitations mention the missing Neutral class",
      any("no Neutral class" in x for x in d["limitations"]))
check("Backend label says binary/English", "binary" in d["backends"]["sentiment"])

print("\n=== 2. Whole CSV with each backend ===")
df, _ = load_feedback_csv("data/sample_feedback.csv")
kpi_by_backend = {}
frames = {}
for name in ("vader", "distilbert"):
    start = time.time()
    out = analyze_dataframe(df, backend=name)
    k = compute_kpis(out["results"], out["backend_used"], out["backends"])
    kpi_by_backend[name], frames[name] = k, out["results"]
    print(f"  {name:<10} used={out['backend_used']:<10} counts={k['counts']} avg={k['avg_sentiment_score']:+.3f} "
          f"classes={k['classes_present']} ({time.time() - start:.1f} s)")
check("Every row used one backend only", frames["distilbert"]["backend_used"].nunique() == 1)
check("Both backends give the same KPI keys", set(kpi_by_backend["vader"]) == set(kpi_by_backend["distilbert"]))
check("DistilBERT has no Neutral reviews", kpi_by_backend["distilbert"]["counts"]["Neutral"] == 0)
check("Counts add up for DistilBERT",
      sum(kpi_by_backend["distilbert"]["counts"].values()) == kpi_by_backend["distilbert"]["total_reviews"])

print("\n=== 3. Where do the two backends disagree? (VADER Neutral rows excluded) ===")
merged = frames["vader"][["customer_id", "feedback", "sentiment"]].merge(
    frames["distilbert"][["customer_id", "sentiment"]], on="customer_id", suffixes=("_vader", "_distilbert"))
comparable = merged[merged["sentiment_vader"] != "Neutral"]
disagree = comparable[comparable["sentiment_vader"] != comparable["sentiment_distilbert"]]
print(f"  Comparable reviews: {len(comparable)} | agree: {len(comparable) - len(disagree)} | disagree: {len(disagree)}")
for row in disagree.itertuples():
    print(f"  {row.customer_id}: VADER {row.sentiment_vader}, DistilBERT {row.sentiment_distilbert} -> {row.feedback}")
neutral_rows = merged[merged["sentiment_vader"] == "Neutral"]
for row in neutral_rows.itertuples():
    print(f"  {row.customer_id}: VADER Neutral, DistilBERT {row.sentiment_distilbert} -> {row.feedback}")
print("  (No human-labelled answers exist, so this shows agreement, not accuracy.)")

print("\n=== 4. Fallback when DistilBERT cannot load ===")
saved_classifier, saved_error = distilbert_backend._classifier, distilbert_backend._load_error
distilbert_backend._classifier = None
distilbert_backend._load_error = "DistilBERT could not be loaded (SimulatedError)."
r = analyze_review("The battery drains very quickly.", backend="distilbert")
check("Single review falls back to VADER", r["backend_used"] == "vader" and r["backend_requested"] == "distilbert")
check("Fallback is explained", any("Used VADER instead" in w for w in r["warnings"]))
out = analyze_dataframe(df, backend="distilbert")
check("Whole CSV falls back consistently", out["backend_used"] == "vader"
      and out["results"]["backend_used"].nunique() == 1 and len(out["results"]) == 20)
check("Fallback limitations are VADER's", any("lexicon" in x for x in out["limitations"]))
distilbert_backend._classifier, distilbert_backend._load_error = saved_classifier, saved_error

print("\n=== 5. Backend that does not exist ===")
r = analyze_review("Great phone", backend="azure")
check("Unknown backend falls back with a warning", r["backend_used"] == "vader" and r["warnings"])

print()
print(f"{sum(results)} of {len(results)} checks passed")
