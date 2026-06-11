"""Golden-set assertions. Runs the deterministic stages without an API key,
so the eval is reproducible by any reviewer with zero credentials.

Each expectation encodes what the tool MUST get right regardless of the LLM:
- the poisoned candidate's injection must be detected (security control)
- the clean candidates must NOT trip the detector (no false positives)
- every report must carry blind spots (the contract is non-optional)
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from workbench.pipeline import evaluate_candidate  # noqa: E402

# The eval is a test; its report output is throwaway. Write to scratch so it
# runs under a read-only repo root (the sandbox). Real reports are produced by
# `workbench evaluate`, which writes to the rw-mounted reports/ directory.
OUT = Path(tempfile.mkdtemp(prefix="golden-"))

CASES = [
    {"id": "c1_strong", "min_anomalies": 0, "max_anomalies": 0},
    {"id": "c2_thin", "min_anomalies": 0, "max_anomalies": 0},
    {"id": "c3_poisoned", "min_anomalies": 3, "max_anomalies": 99},
    {"id": "c4_pdf_resume", "min_anomalies": 1, "max_anomalies": 99},
    {"id": "c5_selftaught", "min_anomalies": 0, "max_anomalies": 0},
    {"id": "c6_mlops", "min_anomalies": 0, "max_anomalies": 0},
    {"id": "c7_ops_path", "min_anomalies": 0, "max_anomalies": 0},
]


def run() -> int:
    out = OUT
    failures = []
    print(f"{'candidate':<14} {'anomalies':>9} {'blind_spots':>11}  result")
    print("-" * 52)
    for case in CASES:
        report = evaluate_candidate(ROOT / "candidates" / case["id"], out)
        n = len(report.anomalies)
        ok = case["min_anomalies"] <= n <= case["max_anomalies"]
        # contract: every report must carry at least one blind spot
        ok = ok and len(report.blind_spots) >= 1
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures.append(case["id"])
        print(f"{case['id']:<14} {n:>9} {len(report.blind_spots):>11}  {status}")

    # specificity check: the injection detector must fire on the poisoned
    # candidate's KINDS, proving it catches all three vectors
    poisoned = evaluate_candidate(ROOT / "candidates" / "c3_poisoned", out)
    kinds = {a.kind for a in poisoned.anomalies}
    needed = {"zero_width_chars", "hidden_html", "injection_phrase"}
    missing = needed - kinds
    print("-" * 52)
    if missing:
        print(f"VECTOR COVERAGE FAIL — missed: {sorted(missing)}")
        failures.append("vector_coverage")
    else:
        print(f"vector coverage OK — caught: {sorted(kinds)}")

    print()
    if failures:
        print(f"GOLDEN SET: FAIL ({len(failures)} issue(s): {failures})")
        return 1
    print("GOLDEN SET: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(run())
