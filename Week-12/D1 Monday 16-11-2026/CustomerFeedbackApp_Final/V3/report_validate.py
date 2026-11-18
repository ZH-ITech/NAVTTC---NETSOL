"""Figure check: every number in a report must exist in the calculated fact sheet."""
import re

from report_facts import allowed_numbers

NUMBER_RE = re.compile(r"(?<![\w.])[-+]?\d+(?:\.\d+)?")
# Time horizons in recommendations ("30-day plan", "within 2 weeks") are not data figures.
HORIZON_RE = re.compile(r"^\s*[-]?\s*(day|days|week|weeks|month|months|hour|hours|year|years)\b", re.I)


def _flatten(sections: dict) -> list:
    texts = []
    for value in sections.values():
        if isinstance(value, str):
            texts.append(value)
        elif isinstance(value, list):
            texts.extend(str(item) for item in value)
    return texts


def check_figures(sections: dict, facts: dict) -> dict:
    allowed = allowed_numbers(facts)
    checked, unverified = 0, []
    for text in _flatten(sections):
        for match in NUMBER_RE.finditer(text):
            if HORIZON_RE.match(text[match.end():]):
                continue
            value = abs(float(match.group()))
            checked += 1
            if not any(abs(value - ok) < 0.0006 for ok in allowed):
                unverified.append(match.group())
    return {
        "numbers_checked": checked,
        "unverified": sorted(set(unverified)),
        "ok": not unverified,
    }
