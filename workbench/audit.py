"""Append-only audit log. Every model interaction is recorded.

Rationale: under Ontario's ESA disclosure rules and Quebec Law 25, an
employer must be able to explain how an AI system participated in a hiring
process. An audit trail is the mechanical precondition for that explanation.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path


class AuditLog:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, stage: str, model: str | None, prompt: str, output: str) -> None:
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "stage": stage,
            "model": model,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "prompt_chars": len(prompt),
            "output": output[:20000],
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
