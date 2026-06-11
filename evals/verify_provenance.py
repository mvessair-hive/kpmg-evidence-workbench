"""Verify the provenance signatures on the committed reports.

For every record in reports/provenance.jsonl, re-read the report it covers,
recompute its content hash, and check the Ed25519 signature against the public
key embedded in the record. A failure means a report was altered after signing,
or a record does not match its report: exactly the "has this been tampered
with" question a hiring system must be able to answer.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from workbench.provenance import verify_record  # noqa: E402

REPORTS = ROOT / "reports"
LEDGER = REPORTS / "provenance.jsonl"


def run() -> int:
    if not LEDGER.exists():
        print("no provenance ledger yet; run `python -m workbench evaluate candidates/ --out reports/` first")
        return 1
    ok = True
    signers = set()
    for line in LEDGER.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        report = REPORTS / f"{rec['candidate_id']}.md"
        if not report.exists():
            print(f"  [MISSING] {rec['candidate_id']}.md referenced by ledger but not found")
            ok = False
            continue
        valid = verify_record(rec, report.read_text())
        signers.add(rec.get("public_key", "")[:16])
        print(f"  [{'ok' if valid else 'TAMPERED'}] {rec['candidate_id']}.md  "
              f"sha256={rec['content_sha256'][:12]}  signer={rec.get('public_key','')[:16]}…")
        ok = ok and valid

    print()
    if ok:
        print(f"PROVENANCE: PASS — every committed report verifies against its signature "
              f"({len(signers)} signer key(s)).")
        return 0
    print("PROVENANCE: FAIL — a report does not match its signature.")
    return 1


if __name__ == "__main__":
    sys.exit(run())
