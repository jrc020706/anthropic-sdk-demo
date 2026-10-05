from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".text"}
PDF_SUFFIXES = {".pdf"}


class UnsupportedDocumentError(ValueError):
    """Raised when a document format cannot be read by the loader."""


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise UnsupportedDocumentError(
            f"'{path.name}' is a PDF but the 'pypdf' package is not installed. "
            "Run: pip install -r requirements.txt"
        ) from exc

    try:
        reader = PdfReader(str(path))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception as exc:
        raise UnsupportedDocumentError(f"'{path.name}' could not be parsed as PDF: {exc}") from exc

    text = "\n\n".join(page for page in pages if page)
    if not text.strip():
        raise UnsupportedDocumentError(
            f"'{path.name}' has no extractable text (it may be a scanned PDF)."
        )
    return text


def load_document(path: Path) -> str:
    """Reads a supported document and returns its plain text content."""
    suffix = path.suffix.lower()

    if suffix in PDF_SUFFIXES:
        return _read_pdf(path)

    if suffix not in SUPPORTED_SUFFIXES:
        raise UnsupportedDocumentError(
            f"'{path.name}' has an unsupported extension '{suffix or '(none)'}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_SUFFIXES | PDF_SUFFIXES))}."
        )

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1", errors="replace")
    except OSError as exc:
        raise UnsupportedDocumentError(f"'{path.name}' could not be read: {exc}") from exc

    if not text.strip():
        raise UnsupportedDocumentError(f"'{path.name}' is empty, so it was skipped.")
    return text


def discover_documents(directory: Path, *, recursive: bool = True) -> List[Path]:
    """Returns candidate documents inside ``directory``, sorted by name."""
    if not directory.exists():
        return []
    pattern = "**/*" if recursive else "*"
    return sorted(
        item
        for item in directory.glob(pattern)
        if item.is_file() and not item.name.startswith(".")
    )


def classify_documents(paths: Iterable[Path]) -> tuple[list[Path], list[Path]]:
    """Splits files into supported documents and unsupported ones."""
    supported: list[Path] = []
    unsupported: list[Path] = []
    for path in paths:
        suffix = path.suffix.lower()
        if suffix in SUPPORTED_SUFFIXES or suffix in PDF_SUFFIXES:
            supported.append(path)
        else:
            unsupported.append(path)
    return supported, unsupported
