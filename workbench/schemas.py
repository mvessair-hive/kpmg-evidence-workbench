"""Data contracts for the Candidate Evidence Workbench.

Every pipeline stage communicates through these models. The LLM is
schema-constrained to them; deterministic stages construct them directly.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ClaimStatus(str, Enum):
    EVIDENCED = "evidenced"
    UNVERIFIED = "unverified"
    FLAGGED = "flagged"


class Claim(BaseModel):
    """A capability claim the candidate makes about themselves."""

    text: str = Field(description="The claim, paraphrased concisely")
    source_file: str = Field(description="File the claim came from")
    quote: str = Field(description="Short verbatim quote supporting the paraphrase")
    rubric_dimension: str = Field(
        description="Which rubric dimension this claim speaks to"
    )


class ExtractionResult(BaseModel):
    claims: List[Claim]
    extraction_notes: List[str] = Field(
        default_factory=list,
        description="Anything the extractor was unsure about or could not parse",
    )


class EvidenceFinding(BaseModel):
    claim: Claim
    status: ClaimStatus
    evidence_pointer: Optional[str] = Field(
        default=None,
        description="Where in the provided materials the evidence lives (file + brief locator). Null if unverified.",
    )
    rationale: str = Field(description="One sentence: why this status")


class MatchResult(BaseModel):
    findings: List[EvidenceFinding]
    matcher_notes: List[str] = Field(default_factory=list)


class InterviewQuestion(BaseModel):
    question: str
    probes_claim: str
    rubric_dimension: str


class AnomalyFinding(BaseModel):
    """Output of the deterministic hidden-content detector."""

    kind: str  # e.g. "zero_width_chars", "hidden_html", "injection_phrase"
    source_file: str
    line: int
    excerpt: str
    explanation: str


class BlindSpot(BaseModel):
    """Something this tool could NOT verify or see. First-class output."""

    category: str  # e.g. "external_link_not_fetched", "no_evidence_channel", "stage_skipped"
    detail: str


class CandidateReport(BaseModel):
    candidate_id: str
    findings: List[EvidenceFinding]
    questions: List[InterviewQuestion]
    anomalies: List[AnomalyFinding]
    blind_spots: List[BlindSpot]
    files_examined: List[str]
    files_skipped: List[str]

    @property
    def evidenced(self) -> List[EvidenceFinding]:
        return [f for f in self.findings if f.status == ClaimStatus.EVIDENCED]

    @property
    def unverified(self) -> List[EvidenceFinding]:
        return [f for f in self.findings if f.status == ClaimStatus.UNVERIFIED]
