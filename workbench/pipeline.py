"""Pipeline orchestration: deterministic spine, LLM in the middle, human at the end."""
from __future__ import annotations

from pathlib import Path
from typing import List

from . import llm
from .audit import AuditLog
from .detector import scan_candidate, scan_file
from .images import IMAGE_EXTS, ImageSignals, analyze_images
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


def _blind_spots(pkg: CandidatePackage, findings: List[EvidenceFinding], llm_ran: bool,
                 imgsig: "ImageSignals | None" = None) -> List[BlindSpot]:
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
    if imgsig is not None and imgsig.count:
        srcs = ", ".join(dict.fromkeys(imgsig.sources))
        if imgsig.ocr_ran:
            detail = (
                f"{imgsig.count} image(s) present ({srcs}). OCR is installed, so the tool read them "
                "and scanned the text for hidden instructions."
            )
        else:
            detail = (
                f"{imgsig.count} image(s) present ({srcs}) and NOT read. A scanned or image-based resume "
                "can carry text a human sees but this text extractor does not. Review the image(s) manually, "
                "or install Tesseract OCR to have the tool read and scan them automatically."
            )
        spots.append(BlindSpot(category="image_content", detail=detail))
    non_image_skipped = [f for f in pkg.skipped if f.suffix.lower() not in IMAGE_EXTS]
    if non_image_skipped:
        spots.append(
            BlindSpot(
                category="files_skipped",
                detail="Unsupported file type(s) not analyzed: " + ", ".join(f.name for f in non_image_skipped),
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

    # Detect image content (standalone, or embedded in PDF/DOCX). If OCR is
    # installed, read the images and scan the text for hidden instructions too.
    standalone_images = [f for f in pkg.skipped if f.suffix.lower() in IMAGE_EXTS]
    docs_for_images = [f for f in pkg.files if f.suffix.lower() in {".pdf", ".docx"}]
    imgsig = analyze_images(standalone_images, docs_for_images)
    if imgsig.ocr_ran and imgsig.ocr_text.strip():
        import tempfile

        scratch = Path(tempfile.mkdtemp()) / "ocr.txt"
        scratch.write_text(imgsig.ocr_text, encoding="utf-8")
        anomalies = anomalies + scan_file(scratch)

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
        blind_spots=_blind_spots(pkg, findings, llm_ran, imgsig),
        files_examined=[f.name for f in pkg.files],
        files_skipped=[f.name for f in pkg.skipped],
    )
