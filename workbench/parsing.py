"""Candidate package loading. Deterministic; declares what it skips."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

SUPPORTED = {".md", ".txt", ".html", ".htm"}

URL = re.compile(r"https?://[^\s)\"'>]+")


@dataclass
class CandidatePackage:
    candidate_id: str
    root: Path
    files: List[Path] = field(default_factory=list)
    skipped: List[Path] = field(default_factory=list)
    external_links: List[str] = field(default_factory=list)

    def combined_text(self) -> str:
        parts = []
        for f in self.files:
            parts.append(f"=== FILE: {f.name} ===\n{f.read_text(encoding='utf-8', errors='replace')}")
        return "\n\n".join(parts)


def load_candidate(root: Path) -> CandidatePackage:
    pkg = CandidatePackage(candidate_id=root.name, root=root)
    for f in sorted(root.iterdir()):
        if not f.is_file():
            continue
        if f.suffix.lower() in SUPPORTED:
            pkg.files.append(f)
            pkg.external_links.extend(URL.findall(f.read_text(encoding="utf-8", errors="replace")))
        else:
            pkg.skipped.append(f)
    # de-dup links, preserve order
    seen = set()
    pkg.external_links = [u for u in pkg.external_links if not (u in seen or seen.add(u))]
    return pkg
