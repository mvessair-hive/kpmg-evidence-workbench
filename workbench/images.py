"""Image-content detection, and optional OCR.

A resume can hide text in an image: a screenshot of a paragraph, a scanned page,
or a picture embedded in a PDF or DOCX. A text extractor never sees it, so the
image is a silent channel.

This module closes that silently. It detects image content (standalone image
files, images embedded in PDF or DOCX, and image-only scanned PDFs) so the
pipeline can DECLARE it as a blind spot: a human is told to review it. If the
optional Tesseract OCR engine is installed, the tool also reads the image text
and runs the injection detector on it; otherwise the declaration stands. The
core path needs no system dependency.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".tif", ".bmp"}


@dataclass
class ImageSignals:
    count: int = 0
    sources: List[str] = field(default_factory=list)
    ocr_text: str = ""
    ocr_ran: bool = False


def _ocr_available() -> bool:
    if shutil.which("tesseract") is None:
        return False
    try:
        import pytesseract  # noqa: F401
        import PIL  # noqa: F401
        return True
    except Exception:
        return False


def _ocr_image_bytes(data: bytes) -> str:
    import io

    import pytesseract
    from PIL import Image

    try:
        return pytesseract.image_to_string(Image.open(io.BytesIO(data))) or ""
    except Exception:
        return ""


def analyze_images(standalone: List[Path], docs: List[Path]) -> ImageSignals:
    """standalone: image files in the candidate dir. docs: pdf/docx to inspect
    for embedded images."""
    sig = ImageSignals()
    ocr = _ocr_available()
    blobs: List[bytes] = []

    for f in standalone:
        if f.suffix.lower() in IMAGE_EXTS:
            sig.count += 1
            sig.sources.append(f.name)
            if ocr:
                try:
                    blobs.append(f.read_bytes())
                except OSError:
                    pass

    for d in docs:
        suf = d.suffix.lower()
        try:
            if suf == ".pdf":
                from pypdf import PdfReader

                reader = PdfReader(str(d))
                for page in reader.pages:
                    imgs = list(getattr(page, "images", []) or [])
                    for im in imgs:
                        sig.count += 1
                        sig.sources.append(f"{d.name} (embedded)")
                        if ocr:
                            blobs.append(im.data)
            elif suf == ".docx":
                from docx import Document

                doc = Document(str(d))
                for rel in doc.part.rels.values():
                    if "image" in rel.reltype:
                        sig.count += 1
                        sig.sources.append(f"{d.name} (embedded)")
                        if ocr:
                            try:
                                blobs.append(rel.target_part.blob)
                            except Exception:
                                pass
        except Exception:
            continue

    if ocr and blobs:
        sig.ocr_ran = True
        sig.ocr_text = "\n".join(_ocr_image_bytes(b) for b in blobs)
    return sig
