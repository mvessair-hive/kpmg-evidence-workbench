"""Edge cases. A tool that processes untrusted input must not crash on bad
input; it should degrade and say what it could not do."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from workbench.pipeline import evaluate_candidate  # noqa: E402
from workbench.parsing import _read_text  # noqa: E402
from workbench.detector import scan_file  # noqa: E402


def test_empty_candidate_dir_does_not_crash(tmp_path):
    cand = tmp_path / "empty"
    cand.mkdir()
    report = evaluate_candidate(cand, tmp_path / "out")
    assert report.candidate_id == "empty"
    assert report.findings == []
    # the contract holds even on empty input: blind spots are always present
    assert len(report.blind_spots) >= 1


def test_malformed_pdf_degrades_gracefully(tmp_path):
    bad = tmp_path / "broken.pdf"
    bad.write_bytes(b"%PDF-1.4 this is not a real pdf body")
    text = _read_text(bad)
    assert isinstance(text, str)  # returns a message, does not raise
    assert "pdf" in text.lower()


def test_unsupported_file_is_skipped_not_read(tmp_path):
    cand = tmp_path / "c"
    cand.mkdir()
    (cand / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\n not really")
    (cand / "resume.md").write_text("I shipped a system and owned its tests.")
    report = evaluate_candidate(cand, tmp_path / "out")
    assert "photo.png" in report.files_skipped
    assert "resume.md" in report.files_examined


def test_binary_file_scan_does_not_raise(tmp_path):
    f = tmp_path / "blob.txt"
    f.write_bytes(bytes(range(256)) * 4)
    # scanning arbitrary bytes must not raise
    result = scan_file(f)
    assert isinstance(result, list)


def test_large_input_is_handled(tmp_path):
    cand = tmp_path / "big"
    cand.mkdir()
    (cand / "resume.md").write_text("skill. " * 50000)  # ~350KB
    report = evaluate_candidate(cand, tmp_path / "out")
    assert report.candidate_id == "big"
