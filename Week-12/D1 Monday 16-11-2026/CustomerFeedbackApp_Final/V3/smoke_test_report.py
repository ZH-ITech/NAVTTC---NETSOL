"""Terminal test for the executive-report engine (offline: no API calls)."""
import json

import pandas as pd

from data_loader import load_feedback_csv
from kpis import compute_kpis
from pipeline import analyze_dataframe
from report_facts import build_facts
from report_service import generate_report
from report_template import build_template_report
from report_validate import check_figures

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS" if ok else "FAIL"), "-", name, extra)


def facts_for(frame, backend="vader"):
    return build_facts(compute_kpis(frame, backend), backend, backend)


print("=== 1. Sample dataset (VADER) ===")
df, _ = load_feedback_csv("data/sample_feedback.csv")
out = analyze_dataframe(df, backend="vader")
facts = build_facts(compute_kpis(out["results"], out["backend_used"], out["backends"]),
                    out["backend_used"], out["backends"]["sentiment"])
report = generate_report(facts, preference="template")
print("Label:", report["label"])
print("Headline:", report["sections"]["headline"])
for key in ("findings", "complaints", "recommendations"):
    print(f"{key.title()}:")
    for line in report["sections"][key]:
        print("  -", line)
print("Caveats:", len(report["sections"]["caveats"]), "lines")
print("Figure check:", report["figure_check"])

check("Fact sheet has no customer IDs or review text",
      not any(cid in json.dumps(facts) for cid in out["results"]["customer_id"])
      and not any(text in json.dumps(facts) for text in out["results"]["feedback"]))
check("Template report passes its own figure check", report["figure_check"]["ok"] and report["figure_check"]["numbers_checked"] > 5)
check("Report says it is template-based", "Template-based" in report["label"] and report["used"] == "template")
check("Same facts give the identical report", build_template_report(facts) == build_template_report(facts))

print("\n=== 2. Figure check catches invented numbers ===")
good = {"headline": "55.0% positive and 40.0% negative (net sentiment +15.0).", "findings": ["Headphones has 4 negative reviews."]}
bad = {"headline": "Negative reviews rose by 12.5% and 77 customers complained."}
horizon = {"recommendations": ["Prepare a 30-day plan and review again within 2 weeks."]}
check("Correct figures pass", check_figures(good, facts)["ok"], str(check_figures(good, facts)))
r = check_figures(bad, facts)
check("Invented figures are caught", not r["ok"] and set(r["unverified"]) == {"12.5", "77"}, str(r))
check("Time horizons are allowed", check_figures(horizon, facts)["ok"])

print("\n=== 3. Edge cases ===")
one = out["results"][out["results"]["product"] == "Laptop"]
f1 = facts_for(one)
r1 = generate_report(f1, "template")
check("One product: no best/weakest claims", "no product comparison" in " ".join(r1["sections"]["findings"]) and r1["figure_check"]["ok"])
tiny = out["results"].head(3)
f2 = facts_for(tiny)
check("Tiny dataset: small-sample caveat", any("Small sample" in c for c in build_template_report(f2)["caveats"]))
positive = out["results"][out["results"]["sentiment"] == "Positive"].copy()
positive["complaint_categories"] = ""
f3 = facts_for(positive)
r3 = generate_report(f3, "template")
check("All-positive data: says no complaints", any("No complaint categories" in c for c in r3["sections"]["complaints"]) and r3["figure_check"]["ok"])
binary = out["results"].copy()
binary["sentiment"] = binary["sentiment"].replace({"Neutral": "Negative"})
f4 = facts_for(binary, "distilbert")
r4 = generate_report(f4, "template")
text4 = json.dumps(r4["sections"])
check("Binary backend: never mentions a Neutral percentage", "neutral" not in r4["sections"]["headline"].lower() and "binary" in text4)
check("Binary backend report passes figure check", r4["figure_check"]["ok"])

print("\n=== 4. Backend selection and honest fallback ===")
auto = generate_report(facts, preference="auto")
check("No key: auto falls back to the template, no warning", auto["used"] == "template" and not auto["warnings"])
forced = generate_report(facts, preference="openai")
check("OpenAI requested without a key: explained", forced["used"] == "template" and any("no API key" in w for w in forced["warnings"]))

print()
print(f"{sum(results)} of {len(results)} checks passed")
