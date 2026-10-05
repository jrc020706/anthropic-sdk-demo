from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from chat_app.domain.models import IngestionReport
from chat_app.infrastructure.rag.chunking import (
    DEFAULT_CHUNK_TOKENS,
    DEFAULT_OVERLAP_RATIO,
    chunk_text,
    estimate_tokens,
)
from chat_app.infrastructure.rag.loaders import (
    UnsupportedDocumentError,
    classify_documents,
    discover_documents,
    load_document,
)


def ingest_directory(
    directory: Path,
    *,
    embedder,
    vector_store,
    chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
    overlap_ratio: float = DEFAULT_OVERLAP_RATIO,
    rebuild: bool = False,
    only: Optional[List[str]] = None,
) -> list[IngestionReport]:
    """Load -> chunk -> overlap -> embed -> store, one report per document."""
    if not directory.exists():
        return [
            IngestionReport(
                document=str(directory),
                error=f"Directory not found: {directory}. Create it and add documents first.",
            )
        ]

    if rebuild:
        removed = vector_store.clear()
        print(f"Cleared the knowledge base ({removed} chunks removed).")

    paths = discover_documents(directory)
    if only:
        wanted = {name.strip() for name in only if name.strip()}
        paths = [path for path in paths if path.name in wanted]
        if not paths:
            return [
                IngestionReport(
                    document=", ".join(sorted(wanted)),
                    error="No matching document found in the knowledge-base folder.",
                )
            ]

    supported, unsupported = classify_documents(paths)
    reports: list[IngestionReport] = []

    for path in unsupported:
        reports.append(
            IngestionReport(
                document=path.name,
                skipped=(
                    f"Unsupported document type '{path.suffix or '(none)'}'; "
                    "supported types are .md, .markdown, .txt and .pdf."
                ),
            )
        )

    for path in supported:
        relative = _relative_source(path, directory)
        try:
            text = load_document(path)
        except UnsupportedDocumentError as exc:
            reports.append(IngestionReport(document=path.name, skipped=str(exc)))
            continue

        try:
            chunks = chunk_text(
                text, target_tokens=chunk_tokens, overlap_ratio=overlap_ratio
            )
        except ValueError as exc:
            reports.append(IngestionReport(document=path.name, error=str(exc)))
            continue

        if not chunks:
            reports.append(IngestionReport(document=path.name, skipped="No text to index."))
            continue

        metadata = [
            {
                "source": relative,
                "document": path.name,
                "chunk_index": index,
                "chunk_tokens": estimate_tokens(chunk),
            }
            for index, chunk in enumerate(chunks)
        ]

        try:
            # Remove previous versions so re-ingestion does not duplicate chunks.
            vector_store.delete_source(relative)
            embeddings = embedder.embed_documents(chunks)
            vector_store.add_chunks(
                contents=chunks, embeddings=embeddings, metadata=metadata
            )
        except Exception as exc:
            reports.append(IngestionReport(document=path.name, error=str(exc)))
            continue

        reports.append(
            IngestionReport(
                document=path.name,
                chunks=len(chunks),
                tokens=sum(estimate_tokens(chunk) for chunk in chunks),
                sources=[relative],
            )
        )

    return reports


def _relative_source(path: Path, directory: Path) -> str:
    """Source label stored in metadata, e.g. ``documents/setup.md``."""
    try:
        return str(path.relative_to(directory.parent))
    except ValueError:
        return path.name
