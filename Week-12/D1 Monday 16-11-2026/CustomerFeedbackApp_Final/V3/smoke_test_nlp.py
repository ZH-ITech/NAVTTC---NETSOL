"""Terminal test for the V1 NLP modules (no Flask needed)."""
from analysis import InvalidReviewError, analyze_review, validate_review

SAMPLES = [
    "Excellent laptop, very fast and reliable.",
    "The battery drains very quickly.",
    "Delivery was delayed by four days.",
    "The product stopped working after two days.",
    "Good performance but expensive.",
    "Customer support was extremely helpful.",
    "Customer service did not resolve my issue.",
    "Poor sound quality and uncomfortable.",
    "Average product, nothing special.",
]

print("Sentiment | Score  | Complaint categories         | Review")
print("-" * 100)
for s in SAMPLES:
    r = analyze_review(s)
    cats = ", ".join(r["complaint_categories"]) or "-"
    print(f"{r['sentiment']['label']:<9} | {r['sentiment']['score']:+.3f} | {cats:<28} | {s}")

r = analyze_review(SAMPLES[1])
print()
print("Key phrases for sample 2:", r["key_phrases"])
print("Backend requested:", r["backend_requested"], "| used:", r["backend_used"])
print("Labels:", r["backends"])

print()
for bad in ["", "   ", "a", "12345 !!!", "x" * 1001]:
    try:
        validate_review(bad)
        print("UNEXPECTED: accepted", repr(bad[:20]))
    except InvalidReviewError as exc:
        print("Rejected as expected:", exc)

print()
r = analyze_review("Great phone", backend="azure")
print("Unavailable backend test ->", r["backend_used"], "|", r["warnings"])

