"""Extract plain text from uploaded CV PDFs."""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Return concatenated text from all PDF pages."""
    if not file_bytes:
        raise ValueError("Empty PDF upload.")

    reader = PdfReader(BytesIO(file_bytes))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text.strip())

    combined = "\n\n".join(parts).strip()
    if not combined:
        raise ValueError(
            "No extractable text in this PDF. Use a text-based CV (not a scanned image)."
        )
    return combined
