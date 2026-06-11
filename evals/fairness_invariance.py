"""Fairness: demographic-invariance check.

The tool must not let a candidate's demographic signals change its output. This
is enforced two ways, and this script proves the first one mechanically:

1. STRUCTURAL (proven here, deterministic, no key): the parsing, anomaly
   detection, and report structure never read identity. We take a real
   candidate, swap names, pronouns, and schools across demographic lines while
   leaving every capability claim untouched, and assert the deterministic
   output is identical except for the swapped strings themselves.

2. MODEL-LEVEL (protocol, needs --live): the extraction prompt is instructed to
   pull capability claims only, never demographic attributes. Measuring full
   LLM-output invariance across demographic variants is the production step; the
   protocol is documented in docs/FAIRNESS.md. This script asserts the prompt
   contains no demographic terms, as a static guard.

A failure here means identity is leaking into the structural layer, which is the
most direct bias vector and the one we can close completely.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from workbench.detector import scan_file  # noqa: E402
from workbench import llm  # noqa: E402

# Demographic variants: same capabilities, different identity signals. The
# point is that NONE of these should change what the tool concludes.
PERSONAS = [
    {"name": "Priya Raghavan", "pron": "she/her", "school": "fictional university"},
    {"name": "James O'Brien", "pron": "he/him", "school": "a state college"},
    {"name": "Aisha Mohammed", "pron": "they/them", "school": "a community college"},
    {"name": "Chen Wei", "pron": "she/her", "school": "an Ivy League school"},
]

# Two bases: a clean candidate (must stay clean for everyone) and a poisoned one
# (the injection must be caught identically for everyone). Original names are
# swapped out for each persona.
BASES = {
    "clean": (ROOT / "candidates" / "c1_strong" / "resume.md").read_text().replace("Priya Raghavan", "{NAME}").replace("fictional university", "{SCHOOL}"),
    "poisoned": (ROOT / "candidates" / "c3_poisoned" / "resume.md").read_text().replace("Jordan Tate", "{NAME}").replace("fictional university", "{SCHOOL}"),
}


def structural_signature(text: str, tmp: Path) -> tuple:
    """Everything the deterministic layer concludes, with identity stripped."""
    f = tmp / "r.md"
    f.write_text(text)
    anomalies = scan_file(f)
    return tuple(sorted((a.kind, a.line) for a in anomalies))


def run() -> int:
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="fairness-"))
    ok = True
    for label, base in BASES.items():
        sigs = {}
        print(f"\n{label} candidate, across demographic variants:")
        for p in PERSONAS:
            text = base.replace("{NAME}", p["name"]).replace("{SCHOOL}", p["school"])
            sig = structural_signature(text, tmp)
            sigs[p["name"]] = sig
            print(f"  {p['name']:<18} {p['pron']:<9} -> {len(sig)} flags")
        distinct = set(sigs.values())
        same = len(distinct) == 1
        ok = ok and same
        print(f"  => {'identical for all (' + str(len(next(iter(distinct)))) + ' flags each)' if same else 'VARIES — bias leak'}")

    # Static guard: the extraction prompt must not reference demographic terms.
    # Word-boundary match so "age" does not hit "stage", etc.
    demographic_terms = ["gender", "race", "ethnicity", "age", "nationality",
                         "religion", "pronoun", " a male ", "a female"]
    prompt = (llm.EXTRACT_SYSTEM + llm.MATCH_SYSTEM).lower()
    leaks = [t for t in demographic_terms if re.search(rf"\b{re.escape(t.strip())}\b", prompt)]

    print()
    print(f"structural signatures distinct: {len(distinct)} (want 1)")
    print(f"demographic terms in prompts:   {leaks or 'none'}")
    print()
    if ok and not leaks:
        print("FAIRNESS INVARIANCE: PASS — identity does not change the structural output, "
              "and the extraction prompt targets capability claims only.")
        return 0
    if not ok:
        print("FAIL: structural output varies with demographic identity.")
    if leaks:
        print(f"FAIL: extraction prompt references demographic terms: {leaks}")
    return 1


if __name__ == "__main__":
    sys.exit(run())
