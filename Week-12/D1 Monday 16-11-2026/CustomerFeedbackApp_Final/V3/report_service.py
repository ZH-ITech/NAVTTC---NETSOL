"""Choose the report backend, label it honestly and fall back to the template when needed."""
from config import REPORT_BACKEND, openai_configured
from report_template import TEMPLATE_LABEL, build_template_report
from report_validate import check_figures


def _openai_module():
    try:
        import report_openai  # added in the next step
    except ImportError:
        return None
    return report_openai


def generate_report(facts: dict, preference: str = None) -> dict:
    preference = preference or REPORT_BACKEND
    warnings = []
    sections, used, label, usage = None, "template", TEMPLATE_LABEL, None

    if preference in ("auto", "openai"):
        if not openai_configured():
            if preference == "openai":
                warnings.append("OpenAI was requested but no API key is configured; the template report was used.")
        else:
            module = _openai_module()
            if module is None:
                warnings.append("The OpenAI report writer is not installed in this version; the template report was used.")
            else:
                draft, reason, usage = module.generate_openai_report(facts)
                if draft is None:
                    warnings.append(f"OpenAI report not used: {reason} The template report was used instead.")
                else:
                    sections, used, label = draft, "openai", module.report_label()

    if sections is None:
        sections = build_template_report(facts)

    return {
        "requested": preference,
        "used": used,
        "label": label,
        "sections": sections,
        "figure_check": check_figures(sections, facts),
        "warnings": warnings,
        "usage": usage,
    }
