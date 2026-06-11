"""Rubric derived transparently from the KPMG AI Builder job description.

Each dimension quotes the JD language it derives from, so a reviewer can
audit the rubric itself. The rubric defines WHAT evidence would look like;
it deliberately does not define scores or weights, humans weigh.
"""
from __future__ import annotations

RUBRIC = [
    {
        "dimension": "enterprise_fluency",
        "jd_basis": "You bring enterprise fluency and understand how organizations operate.",
        "evidence_looks_like": "Work delivered inside large/regulated organizations; navigating multiple stakeholders.",
    },
    {
        "dimension": "workflow_thinking",
        "jd_basis": "You think in workflows, not just models, designing multi-step processes that account for human-AI handoffs, decision boundaries, and appropriate levels of autonomy.",
        "evidence_looks_like": "Designs showing explicit human-AI handoffs, decision boundaries, autonomy levels.",
    },
    {
        "dimension": "builder_shipping",
        "jd_basis": "You have a builder mindset and don't just describe solutions, you create them.",
        "evidence_looks_like": "Shipped, inspectable artifacts: live products, repos, demos — not descriptions of ideas.",
    },
    {
        "dimension": "end_to_end_ownership",
        "jd_basis": "You take end-to-end ownership, from problem definition through to a working system that people actually use.",
        "evidence_looks_like": "Same person visible from problem framing to operation/maintenance of a used system.",
    },
    {
        "dimension": "ambiguity",
        "jd_basis": "You're comfortable operating in ambiguity and understand that enterprise transformation is rarely linear.",
        "evidence_looks_like": "Open-ended problems scoped into concrete directions; documented reframing decisions.",
    },
    {
        "dimension": "evaluation_discipline",
        "jd_basis": "Work with production systems, design evaluations... build, test, and iterate with intention.",
        "evidence_looks_like": "Eval harnesses, test suites, adversarial testing wired into delivery — not claimed QA in prose.",
    },
    {
        "dimension": "responsible_ai",
        "jd_basis": "You apply sound judgment, treating risk, governance, ethics, and trust as core design constraints rather than afterthoughts.",
        "evidence_looks_like": "Guardrails present in the artifact itself: HITL gates, privacy choices, audit trails, refusal paths.",
    },
]


def rubric_for_prompt() -> str:
    lines = []
    for r in RUBRIC:
        lines.append(
            f"- {r['dimension']}: {r['jd_basis']} (Evidence looks like: {r['evidence_looks_like']})"
        )
    return "\n".join(lines)


def dimensions() -> list[str]:
    return [r["dimension"] for r in RUBRIC]
