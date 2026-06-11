"""CLI: python -m workbench evaluate <candidate_dir> [--out reports/]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import evaluate_candidate
from .report import render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="workbench", description="Candidate Evidence Workbench")
    sub = parser.add_subparsers(dest="cmd", required=True)
    ev = sub.add_parser("evaluate", help="Evaluate one candidate directory, or a directory of candidates")
    ev.add_argument("path", type=Path)
    ev.add_argument("--out", type=Path, default=Path("reports"))
    args = parser.parse_args(argv)

    roots = [args.path]
    if not any(f.is_file() for f in args.path.iterdir()):
        roots = sorted(p for p in args.path.iterdir() if p.is_dir())

    args.out.mkdir(parents=True, exist_ok=True)
    for root in roots:
        report = evaluate_candidate(root, args.out)
        out_file = args.out / f"{report.candidate_id}.md"
        out_file.write_text(render(report), encoding="utf-8")
        flag = " ⚠ ANOMALIES" if report.anomalies else ""
        print(
            f"{report.candidate_id}: {len(report.evidenced)} evidenced, "
            f"{len(report.unverified)} unverified, {len(report.questions)} questions, "
            f"{len(report.blind_spots)} blind spots{flag} -> {out_file}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
