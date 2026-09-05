"""Extract plain text from uploaded .txt / .pdf documents."""

from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfReader

ALLOWED_EXTENSIONS = {".txt", ".text", ".md", ".pdf"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB


def _suffix(filename: str | None) -> str:
    return Path(filename or "").suffix.lower()


def assert_allowed_filename(filename: str | None) -> str:
    ext = _suffix(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Only .txt, .md, or .pdf files are supported")
    return ext


def extract_text_from_bytes(data: bytes, filename: str | None) -> str:
    if not data:
        raise ValueError("Empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("File too large (max 8 MB)")
    ext = assert_allowed_filename(filename)
    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
    else:
        text = data.decode("utf-8", errors="replace").strip()
    if not text:
        raise ValueError("Could not extract text from file")
    return text
