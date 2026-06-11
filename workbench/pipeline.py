"""Pipeline orchestration: deterministic spine, LLM in the middle, human at the end."""
from __future__ import annotations

from pathlib import Path
from typing import List

from . import llm
from .audit import AuditLog
from .detector import scan_candidate
from .parsing import CandidatePackage, load_candidate
from .rubric import dimensions
from .schemas import (
    BlindSpot,
    CandidateReport,
    ClaimStatus,
    EvidenceFinding,
    InterviewQuestion,
)


def _questions_from_unverified(findings: List[EvidenceFinding]) -> List[InterviewQuestion]:
    """Deterministic conversion: every unverified claim becomes a probe.

    The phrasing is intentionally template-based — generating 'clever'
    questions with an LLM here would add variance to the one output a
    human relies on most. Boring and consistent beats creative and drifty.
    """
    questions = []
    for f in findings:
        if f.status is not ClaimStatus.UNVERIFIED:
            continue
        questions.append(
            InterviewQuestion(
                question=(
                    f"You note that {f.claim.text.rstrip('.').lower()}. "
                    "Walk me through a concrete example: what did you build or decide, "
                    "what was the hard tradeoff, and how did you know it worked?"
                ),
                probes_claim=f.claim.text,
                rubric_dimension=f.claim.rubric_dimension,
            )
        )
    return questions


def _blind_spots(pkg: CandidatePackage, findings: List[EvidenceFinding], llm_ran: bool) -> List[BlindSpot]:
    spots: List[BlindSpot] = []
    if pkg.external_links:
        spots.append(
            BlindSpot(
                category="external_links_not_fetched",
                detail=(
                    f"{len(pkg.external_links)} external link(s) present but NOT fetched by design "
                    f"(no outbound requests; links may be live, dead, or different from described): "
                    + ", ".join(pkg.external_links[:5])
                    + ("…" if len(pkg.external_links) > 5 else "")
                ),
            )
        )
    if pkg.skipped:
        spots.append(
            BlindSpot(
                category="files_skipped",
                detail="Unsupported file type(s) not analyzed: " + ", ".join(f.name for f in pkg.skipped),
            )
        )
    covered = {f.claim.rubric_dimension for f in findings}
    silent = [d for d in dimensions() if d not in covered]
    if silent:
        spots.append(
            BlindSpot(
                category="rubric_dimensions_silent",
                detail=(
                    "No claims found for: " + ", ".join(silent) +
                    ". Silence is not absence; the candidate may simply not have written about these. Probe in interview."
                ),
            )
        )
    if not llm_ran:
        spots.append(
            BlindSpot(
                category="stage_skipped",
                detail="Claim extraction and evidence matching DID NOT RUN (no API key). Only deterministic checks below are valid.",
            )
        )
    spots.append(
        BlindSpot(
            category="inherent_limits",
            detail=(
                "This tool verifies claims only against the candidate's own submitted materials. "
                "It cannot verify employment history, references, or authorship, and it cannot assess "
                "interpersonal skills. Those remain human work."
            ),
        )
    )
    return spots


def evaluate_candidate(root: Path, out_dir: Path, live: bool = False) -> CandidateReport:
    pkg = load_candidate(root)
    audit = AuditLog(out_dir / "audit_log.jsonl")

    anomalies = scan_candidate(pkg.files)  # deterministic, always runs

    findings: List[EvidenceFinding] = []
    llm_ran = False
    try:
        text = pkg.combined_text()
        extraction = llm.extract_claims(text, audit, candidate_id=pkg.candidate_id, live=live)
        match = llm.match_evidence(text, extraction, audit, candidate_id=pkg.candidate_id, live=live)
        findings = match.findings
        llm_ran = True
    except llm.LLMUnavailable:
        pass

    return CandidateReport(
        candidate_id=pkg.candidate_id,
        findings=findings,
        questions=_questions_from_unverified(findings),
        anomalies=anomalies,
        blind_spots=_blind_spots(pkg, findings, llm_ran),
        files_examined=[f.name for f in pkg.files],
        files_skipped=[f.name for f in pkg.skipped],
    )
