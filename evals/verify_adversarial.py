"""Adversarial-content accountability check.

Scans every candidate text file for by-design injection / hidden-text payloads.
Any file that contains such content MUST be declared in
security/adversarial-manifest.tsv with a matching sha256. An undeclared file
with adversarial content is a FAILURE: it is either content that leaked in from
outside, or self-generated adversarial content that was never inventoried. Both
are exactly the condition that caused real confusion during this build.

This is the control that answers "identify the nefarious items you generate":
nefarious-by-design content is only allowed in the repo if it is fingerprinted
and accounted for here.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from workbench.detector import scan_file  # noqa: E402

MANIFEST = ROOT / "security" / "adversarial-manifest.tsv"
SCAN_ROOTS = [ROOT / "candidates"]


def load_manifest() -> dict[str, str]:
    declared: dict[str, str] = {}
    if not MANIFEST.exists():
        return declared
    for line in MANIFEST.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            declared[parts[1]] = parts[0]  # path -> sha256
    return declared


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run() -> int:
    declared = load_manifest()
    problems: list[str] = []
    found_adversarial: list[str] = []

    for base in SCAN_ROOTS:
        for f in base.rglob("*"):
            if not f.is_file():
                continue
            if scan_file(f):  # file contains adversarial content
                rel = str(f.relative_to(ROOT))
                found_adversarial.append(rel)
                if rel not in declared:
                    problems.append(f"UNDECLARED adversarial content: {rel} (not in manifest)")
                elif declared[rel] != sha256(f):
                    problems.append(f"HASH MISMATCH: {rel} (manifest hash != file hash; content changed)")

    # A declared file that no longer has adversarial content, or is missing.
    for path in declared:
        p = ROOT / path
        if not p.exists():
            problems.append(f"DECLARED file missing: {path}")

    print(f"adversarial files found:    {len(found_adversarial)}")
    print(f"declared in manifest:       {len(declared)}")
    for rel in sorted(found_adversarial):
        mark = "ok" if rel in declared and declared[rel] == sha256(ROOT / rel) else "UNACCOUNTED"
        print(f"  [{mark}] {rel}")

    print()
    if problems:
        for p in problems:
            print("FAIL:", p)
        print("\nADVERSARIAL ACCOUNTABILITY: FAIL")
        return 1
    print("ADVERSARIAL ACCOUNTABILITY: PASS — all adversarial content is inventoried and hash-matched.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
