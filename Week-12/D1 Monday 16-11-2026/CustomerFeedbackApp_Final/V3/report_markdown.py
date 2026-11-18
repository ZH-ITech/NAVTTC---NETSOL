"""Markdown export for Customer Feedback Intelligence executive reports."""

from datetime import datetime


def _as_bullets(items):
    if not items:
        return "- No items available."
    return "\n".join(f"- {item}" for item in items)


def build_markdown_report(report, facts, source_name="Uploaded dataset"):
    sections = report.get("sections", {})
    dataset = facts.get("dataset", {})
    sentiment = facts.get("sentiment", {})
    complaints = facts.get("complaints", {})

    lines = [
        "# Customer Feedback Intelligence",
        "## Executive Report",
        "",
        f"**Source:** {source_name}",
        f"**Generated:** {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}",
        f"**Reviews analysed:** {dataset.get('reviews_analysed', 0)}",
        f"**Sentiment backend:** {dataset.get('sentiment_backend', 'Unknown')}",
        f"**Report method:** {report.get('label', 'Unknown')}",
        "",
        "---",
        "",
        "## Executive headline",
        "",
        str(sections.get("headline", "No headline available.")),
        "",
        "## Key findings",
        "",
        _as_bullets(sections.get("findings", [])),
        "",
        "## Complaint analysis",
        "",
        _as_bullets(sections.get("complaints", [])),
        "",
        "## Recommendations",
        "",
        _as_bullets(sections.get("recommendations", [])),
        "",
        "## Caveats and limitations",
        "",
        _as_bullets(sections.get("caveats", [])),
        "",
        "## Calculated sentiment snapshot",
        "",
        f"- Positive: {sentiment.get('positive', {}).get('pct', 'N/A')}%",
        f"- Neutral: {sentiment.get('neutral', {}).get('pct', 'Not supported') if sentiment.get('neutral') is not None else 'Not supported'}",
        f"- Negative: {sentiment.get('negative', {}).get('pct', 'N/A')}%",
        f"- Net sentiment: {sentiment.get('net_sentiment', 'N/A')}",
        f"- Reviews with complaint flags: {complaints.get('reviews_with_complaint_flag', 'N/A')}",
        "",
        "---",
        "",
        "*This report is based on aggregated analysis results. It does not include customer IDs or raw review text.*",
        "",
    ]

    figure_check = report.get("figure_check", {})
    lines.extend([
        "## Numerical validation",
        "",
        f"- Validation status: {'Passed' if figure_check.get('ok') else 'Needs review'}",
        f"- Numbers checked: {figure_check.get('numbers_checked', 0)}",
    ])

    unverified = figure_check.get("unverified", [])
    if unverified:
        lines.append(f"- Unverified figures: {', '.join(map(str, unverified))}")

    warnings = report.get("warnings", [])
    if warnings:
        lines.extend(["", "## Generation warnings", "", _as_bullets(warnings)])

    return "\n".join(lines)
