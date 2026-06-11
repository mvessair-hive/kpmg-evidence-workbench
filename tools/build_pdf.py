#!/usr/bin/env python3
"""Render docs/WRITEUP.md to Mitchell_Vessair_AIBuilder.pdf via headless Chrome.

Markdown -> styled HTML -> print-to-pdf. No network. Reproducible: same input
gives the same PDF layout. Chrome is the only external dependency.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "WRITEUP.md"
OUT = ROOT / "Mitchell_Vessair_AIBuilder.pdf"

CSS = """
@page { size: letter; margin: 0.9in 0.85in; }
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica,
    Arial, sans-serif;
  font-size: 10.5pt; line-height: 1.5; color: #1a1a1a; max-width: 100%;
}
h1 { font-size: 19pt; margin: 0 0 4pt; line-height: 1.2; }
h2 { font-size: 13pt; margin: 18pt 0 6pt; border-bottom: 1px solid #ddd;
  padding-bottom: 3pt; }
h3 { font-size: 11pt; margin: 12pt 0 4pt; }
p { margin: 6pt 0; }
code { font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 9pt;
  background: #f4f4f4; padding: 1px 4px; border-radius: 3px; }
pre { background: #f6f8fa; padding: 10pt; border-radius: 5px; overflow-x: auto;
  font-size: 8.5pt; line-height: 1.45; }
pre code { background: none; padding: 0; }
ul, ol { margin: 6pt 0; padding-left: 20pt; }
li { margin: 2pt 0; }
strong { color: #000; }
a { color: #0b5fa5; text-decoration: none; }
hr { border: none; border-top: 1px solid #ddd; margin: 14pt 0; }
table { border-collapse: collapse; width: 100%; font-size: 9.5pt; margin: 8pt 0; }
th, td { border: 1px solid #ccc; padding: 4pt 7pt; text-align: left; }
th { background: #f4f4f4; }
"""


def build() -> None:
    text = SRC.read_text(encoding="utf-8")
    body = markdown.markdown(
        text, extensions=["extra", "sane_lists", "tables", "fenced_code"]
    )
    html = (
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{CSS}</style></head><body>{body}</body></html>"
    )
    with tempfile.TemporaryDirectory() as td:
        html_path = Path(td) / "writeup.html"
        html_path.write_text(html, encoding="utf-8")
        chrome = next(
            (c for c in ("google-chrome", "chromium", "chromium-browser")
             if _which(c)), None,
        )
        if not chrome:
            sys.exit("No Chrome/Chromium found to render the PDF.")
        subprocess.run(
            [chrome, "--headless", "--no-sandbox", "--disable-gpu",
             "--no-pdf-header-footer", f"--print-to-pdf={OUT}",
             html_path.as_uri()],
            check=True, capture_output=True,
        )
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


def _which(name: str) -> bool:
    from shutil import which
    return which(name) is not None


if __name__ == "__main__":
    build()
