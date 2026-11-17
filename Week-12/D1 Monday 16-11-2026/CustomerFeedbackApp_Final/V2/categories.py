"""Rule-based complaint categories (keyword matching). Local, no model."""
import re

CATEGORY_METHOD_LABEL = "Rule-based keyword matching (local)"

# "topic" = the review mentions this area.
# "negative" = wording that is a complaint on its own.
CATEGORY_RULES = {
    "Delivery": {
        "topic": [r"deliver\w*", r"shipp\w*", r"courier", r"packag\w*", r"arriv\w*"],
        "negative": [r"delay\w*", r"late", r"lost", r"never arrived", r"took too long"],
    },
    "Battery": {
        "topic": [r"batter\w*", r"charg\w*", r"drain\w*"],
        "negative": [r"drain\w*", r"dies", r"died", r"does not last", r"doesn't last"],
    },
    "Product Quality / Defect": {
        "topic": [r"quality", r"defect\w*", r"broke\w*", r"damag\w*", r"stopped working"],
        "negative": [r"stopped working", r"not working", r"does not work", r"doesn't work",
                     r"broke\w*", r"defect\w*", r"damag\w*", r"faulty", r"poor quality", r"crack\w*"],
    },
    "Performance": {
        "topic": [r"performance", r"speed", r"slow", r"lag\w*", r"fast"],
        "negative": [r"slow", r"lag\w*", r"freez\w*", r"crash\w*", r"hang\w*", r"overheat\w*"],
    },
    "Display / Screen": {
        "topic": [r"screen", r"display", r"resolution", r"brightness"],
        "negative": [r"dim", r"flicker\w*", r"blurry"],
    },
    "Sound / Audio": {
        "topic": [r"sound", r"audio", r"bass", r"volume", r"mic\w*"],
        "negative": [r"distort\w*", r"muffled", r"crackl\w*", r"tinny"],
    },
    "Comfort / Design / Usability": {
        "topic": [r"comfort\w*", r"uncomfortable", r"design", r"keyboard", r"fit", r"heavy"],
        "negative": [r"uncomfortable", r"heavy", r"bulky"],
    },
    "Price / Value": {
        "topic": [r"price\w*", r"expensive", r"overpriced", r"cost\w*", r"value"],
        "negative": [r"expensive", r"overpriced", r"costly", r"not worth", r"too much"],
    },
    "Customer Support": {
        "topic": [r"customer (?:service|support)", r"support", r"refund\w*", r"warranty"],
        "negative": [r"did not resolve", r"didn't resolve", r"no response", r"unhelpful",
                     r"rude", r"never replied", r"not helpful"],
    },
}


def _compile(patterns):
    return re.compile(r"\b(?:" + "|".join(patterns) + r")\b", re.IGNORECASE)


_COMPILED = {
    name: {"topic": _compile(rules["topic"]), "negative": _compile(rules["negative"])}
    for name, rules in CATEGORY_RULES.items()
}


def detect_complaint_categories(text: str, sentiment_label: str) -> list:
    """Flag a category if its negative wording matches, or if its topic matches
    and the overall sentiment is Negative. Negative review with no match
    becomes 'Other / Unspecified'."""
    found = []
    for name, rx in _COMPILED.items():
        if rx["negative"].search(text) or (
            sentiment_label == "Negative" and rx["topic"].search(text)
        ):
            found.append(name)
    if sentiment_label == "Negative" and not found:
        found.append("Other / Unspecified")
    return found
