"""Deterministic hidden-content and prompt-injection detector.

This stage is intentionally NOT an LLM. Detection of adversarial content is
a security control, and security controls should be inspectable, testable,
and immune to the attack class they detect. An LLM cross-check can be added
as a second opinion, but the deterministic pass is the control of record.

Documented attack: hidden text in resumes addressed to AI screeners
(white-on-white fonts, zero-width characters, HTML comments). Found in
roughly 1-10%% of AI-scanned resumes per industry reporting (ManpowerGroup,
Greenhouse, 2024-2026).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from .schemas import AnomalyFinding

ZERO_WIDTH = re.compile(r"[​‌‍⁠﻿]")

HIDDEN_HTML_STYLE = re.compile(
    r"""style\s*=\s*["'][^"']*(
        color\s*:\s*(\#fff(?:fff)?|white|rgba?\(\s*255\s*,\s*255\s*,\s*255)
      | font-size\s*:\s*0
      | display\s*:\s*none
      | visibility\s*:\s*hidden
      | opacity\s*:\s*0(?:\.0+)?\s*[;"']
    )""",
    re.IGNORECASE | re.VERBOSE,
)

HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.DOTALL)

INJECTION_PHRASES = re.compile(
    r"""(
        (ignore|disregard|forget|override)\W+(all\W+)?(previous|prior|above|earlier)\W+\w*\W*(instruction|prompt|rule|context)
      | (ignore|disregard|forget|override)\W+(your|the|its)\W+(\w+\W+){0,2}(instruction|prompt|rule|context|rubric|evaluation|guideline|criteria|scoring)
      | rate\W+(this|the)\W+candidate
      | (exceptionally|extremely|highly)\W+(well\W+)?qualified\W+candidate
      | you\W+(must|should|will)\W+(recommend|rank|score|rate|advance|select)
      | (best|top|strongest)\W+candidate\W+(you|in)\W+
      | system\W+prompt
      | (hello|dear|attention|note)\W+(to\W+)?(the\W+)?(ai|assistant|model|screener|llm|reviewer)
      | do\W+not\W+(flag|reject|filter)
    )""",
    re.IGNORECASE | re.VERBOSE,
)


def _scan_lines(path: Path, text: str) -> List[AnomalyFinding]:
    findings: List[AnomalyFinding] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if ZERO_WIDTH.search(line):
            findings.append(
                AnomalyFinding(
                    kind="zero_width_chars",
                    source_file=path.name,
                    line=i,
                    excerpt=line.strip()[:120] or "(invisible characters)",
                    explanation="Zero-width Unicode characters present, invisible to a human reader but visible to a parser.",
                )
            )
        if HIDDEN_HTML_STYLE.search(line):
            findings.append(
                AnomalyFinding(
                    kind="hidden_html",
                    source_file=path.name,
                    line=i,
                    excerpt=line.strip()[:160],
                    explanation="Content styled to be invisible or near-invisible to a human reader.",
                )
            )
        if INJECTION_PHRASES.search(line):
            findings.append(
                AnomalyFinding(
                    kind="injection_phrase",
                    source_file=path.name,
                    line=i,
                    excerpt=line.strip()[:160],
                    explanation="Text pattern consistent with instructions addressed to an AI screener rather than a human reader.",
                )
            )
    return findings


import base64 as _b64

# Encoded / obfuscated payloads. An attacker who knows we scan plaintext will
# encode the instruction. We decode candidate blobs and re-scan, and we flag
# mixed-script tokens (homoglyph evasion: Latin text with Cyrillic/Greek
# lookalikes). These are the "cryptic message" defences.
B64_BLOB = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")
# Confusable ranges: Cyrillic (0400-04FF) and Greek (0370-03FF) letters that
# look like Latin. A token mixing ASCII letters with these is a homoglyph evasion.
CONFUSABLE = re.compile(r"[Ѐ-ӿͰ-Ͽ]")
ASCII_LETTER = re.compile(r"[A-Za-z]")
SUSPICIOUS_DECODED = re.compile(
    r"(ignore|disregard|override|instruction|prompt|rubric|recommend|hire|"
    r"rate this|top candidate|do not (flag|reject)|system prompt)",
    re.IGNORECASE,
)


def _scan_encoded(path: Path, text: str) -> List[AnomalyFinding]:
    findings: List[AnomalyFinding] = []
    # base64 blobs that decode to suspicious text
    for m in B64_BLOB.finditer(text):
        blob = m.group(0)
        try:
            decoded = _b64.b64decode(blob + "=" * (-len(blob) % 4), validate=True).decode("utf-8", "ignore")
        except Exception:
            continue
        if len(decoded) >= 6 and SUSPICIOUS_DECODED.search(decoded):
            line = text[: m.start()].count("\n") + 1
            findings.append(
                AnomalyFinding(
                    kind="encoded_payload",
                    source_file=path.name,
                    line=line,
                    excerpt=f"{blob[:40]}... -> decodes to: {decoded[:80]}",
                    explanation="Base64-encoded text that decodes to instructions addressed to an AI screener.",
                )
            )
    # mixed-script (homoglyph) tokens
    for i, line in enumerate(text.splitlines(), start=1):
        for token in line.split():
            if CONFUSABLE.search(token) and ASCII_LETTER.search(token):
                findings.append(
                    AnomalyFinding(
                        kind="homoglyph_obfuscation",
                        source_file=path.name,
                        line=i,
                        excerpt=token[:60],
                        explanation="Token mixes Latin letters with Cyrillic/Greek lookalikes, a common evasion of text filters.",
                    )
                )
                break
    return findings


def _scan_comments(path: Path, text: str) -> List[AnomalyFinding]:
    findings: List[AnomalyFinding] = []
    for m in HTML_COMMENT.finditer(text):
        body = m.group(1).strip()
        if not body:
            continue
        line = text[: m.start()].count("\n") + 1
        if INJECTION_PHRASES.search(body) or len(body) > 200:
            findings.append(
                AnomalyFinding(
                    kind="comment_payload",
                    source_file=path.name,
                    line=line,
                    excerpt=body[:160],
                    explanation="HTML comment carries substantive text a human reader never sees.",
                )
            )
    return findings


def scan_file(path: Path) -> List[AnomalyFinding]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    findings = _scan_lines(path, text)
    findings += _scan_encoded(path, text)
    if path.suffix.lower() in {".html", ".htm", ".md"}:
        findings += _scan_comments(path, text)
    return findings


def scan_candidate(files: List[Path]) -> List[AnomalyFinding]:
    findings: List[AnomalyFinding] = []
    for f in files:
        findings.extend(scan_file(f))
    return findings
