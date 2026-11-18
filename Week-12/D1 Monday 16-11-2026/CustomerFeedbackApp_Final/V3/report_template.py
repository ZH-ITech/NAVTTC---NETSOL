"""Template-based executive report: fixed rules turn the fact sheet into text. No generative model."""

TEMPLATE_LABEL = "Template-based report (no generative model used)"

ACTIONS = {
    "Delivery": "Review courier performance and packaging standards with the logistics team.",
    "Battery": "Investigate battery life with engineering and check whether charging or power settings need a fix.",
    "Product Quality / Defect": "Audit quality control and returns for the affected products and agree a fix-or-replace policy.",
    "Performance": "Profile the reported slowdowns with engineering and prioritise the most frequent causes.",
    "Display / Screen": "Inspect the display supplier and test units for the reported screen problems.",
    "Sound / Audio": "Test audio output against the reported complaints and review the audio component supplier.",
    "Comfort / Design / Usability": "Run a usability or comfort review with a small customer panel before the next design change.",
    "Price / Value": "Review pricing and the value message against competitors for the affected products.",
    "Customer Support": "Review support case handling and response quality, starting with unresolved cases.",
    "Other / Unspecified": "Read the negative reviews that no rule matched and add categories for any new themes.",
}


def _plural(n: int, word: str = "review") -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _tone(net: float) -> str:
    if net >= 30:
        return "Overall feedback is strongly positive"
    if net >= 10:
        return "Overall feedback is mostly positive"
    if net > -10:
        return "Overall feedback is mixed"
    return "Overall feedback is mostly negative"


def build_template_report(facts: dict) -> dict:
    data = facts["dataset"]
    sent = facts["sentiment"]
    total = data["reviews_analysed"]

    pos, neg, neu = sent["positive"], sent["negative"], sent["neutral"]
    parts = f"{pos['pct']}% positive and {neg['pct']}% negative"
    if neu is not None:
        parts = f"{pos['pct']}% positive, {neu['pct']}% neutral and {neg['pct']}% negative"
    headline = (f"{_tone(sent['net_sentiment'])}: of {_plural(total)} analysed, {parts} "
                f"(net sentiment {sent['net_sentiment']:+.1f}).")

    findings = []
    products = facts["products"]
    if facts["best_product"] and facts["weakest_product"]:
        best, worst = facts["best_product"], facts["weakest_product"]
        findings.append(f"{best['product']} has the highest average sentiment score ({best['avg_score']:+.3f}); "
                        f"{worst['product']} has the lowest ({worst['avg_score']:+.3f}).")
    if len(products) >= 2:
        top_neg = max(products, key=lambda p: p["negative_pct"])
        if top_neg["negative"] > 0:
            findings.append(f"{top_neg['product']} has the highest share of negative reviews: "
                            f"{top_neg['negative']} of {top_neg['reviews']} ({top_neg['negative_pct']}%).")
    elif len(products) == 1:
        only = products[0]
        findings.append(f"Only one product ({only['product']}) is in this dataset, so no product comparison is possible.")
    if neu is None:
        findings.append("The sentiment backend is binary: it has no Neutral class, so mixed or neutral reviews are counted as Positive or Negative.")

    comp = facts["complaints"]
    complaints = []
    for item in comp["top_categories"][:3]:
        complaints.append(f"{item['category']}: flagged in {_plural(item['count'])} ({item['pct_of_reviews']}% of all reviews).")
    if not complaints:
        complaints.append("No complaint categories were flagged in this dataset.")
    hidden = comp["complaints_inside_non_negative_reviews"]
    if hidden:
        complaints.append(f"{_plural(hidden)} with a complaint flag were not labelled Negative by the sentiment backend, "
                          f"so sentiment alone understates complaints.")

    recommendations = []
    for item in comp["top_categories"][:3]:
        action = ACTIONS.get(item["category"])
        if action:
            recommendations.append(f"{action} (Evidence: {item['category']} flagged in {_plural(item['count'])}.)")
    weakest = facts["weakest_product"]
    if weakest:
        recommendations.insert(0, f"Prioritise {weakest['product']}, which has the lowest average sentiment score.")
    if not recommendations:
        recommendations.append("No action is suggested from this dataset because no complaint categories were flagged.")

    caveats = []
    if data["sample_size_warning"]:
        caveats.append(data["sample_size_warning"])
    caveats.extend(facts["limitations"])
    caveats.append("Recommendations here are generic actions mapped from complaint categories. They are not root-cause findings.")
    caveats.append("Tone words (strongly positive, mostly positive, mixed, mostly negative) come from fixed thresholds on net sentiment.")

    return {"headline": headline, "findings": findings, "complaints": complaints,
            "recommendations": recommendations, "caveats": caveats}
