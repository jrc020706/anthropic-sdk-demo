"""Command line interface for the document ingestion pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from chat_app.infrastructure.config import documents_dir
from chat_app.infrastructure.rag import (
    DEFAULT_CHUNK_TOKENS,
    DEFAULT_OVERLAP_RATIO,
    discover_documents,
    load_document,
)
from chat_app.infrastructure.rag.chunking import CHARS_PER_TOKEN, chunk_text, estimate_tokens
from chat_app.infrastructure.rag.ingestion import ingest_directory
from chat_app.infrastructure.rag.loaders import UnsupportedDocumentError, classify_documents


def _preview(directory: Path, chunk_tokens: int, overlap_ratio: float) -> int:
    """Shows the chunking result without calling any external service."""
    if not directory.exists():
        print(f"Error: directory not found: {directory}")
        return 1

    paths = discover_documents(directory)
    if not paths:
        print(f"No documents found in {directory}")
        return 1

    supported, unsupported = classify_documents(paths)
    for path in unsupported:
        print(f"[skipped] {path.name}: unsupported type '{path.suffix or '(none)'}'.")

    total_chunks = 0
    for path in supported:
        try:
            text = load_document(path)
        except UnsupportedDocumentError as exc:
            print(f"[skipped] {exc}")
            continue
        chunks = chunk_text(text, target_tokens=chunk_tokens, overlap_ratio=overlap_ratio)
        total_chunks += len(chunks)
        sizes = [estimate_tokens(chunk) for chunk in chunks]
        ordered = ", ".join(str(size) for size in sizes)
        overlaps = []
        for index in range(1, len(chunks)):
            previous, current = chunks[index - 1], chunks[index]
            # Theoretical maximum overlap of the splitter, plus a small margin.
            tail_size = int(chunk_tokens * CHARS_PER_TOKEN * overlap_ratio) + 64
            tail = previous[-tail_size:] if tail_size else ""
            shared = len(_longest_suffix_prefix(tail, current))
            overlaps.append(round(shared / max(1, len(previous)) * 100))
        overlap_info = f", overlap%: {overlaps}" if overlaps else ""
        print(
            f"[chunked] {path.name}: {len(chunks)} chunks, "
            f"tokens {ordered} (target {chunk_tokens}){overlap_info}"
        )

    print(
        f"\nPreview only (nothing was embedded). Total: {total_chunks} chunks "
        f"from {len(supported)} document(s)."
    )
    print("Run without --preview to embed and store them in Supabase.")
    return 0


def _longest_suffix_prefix(tail: str, current: str) -> str:
    """Returns the text of ``tail`` that is also the start of ``current``."""
    for size in range(min(len(tail), len(current)), 0, -1):
        if current.startswith(tail[-size:]):
            return tail[-size:]
    return ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest documents: load -> chunk -> overlap -> embed -> store."
    )
    parser.add_argument(
        "--documents",
        default=None,
        help="Folder with the knowledge-base documents (default: data/documents)",
    )
    parser.add_argument(
        "--chunk-tokens",
        type=int,
        default=DEFAULT_CHUNK_TOKENS,
        help=f"Target tokens per chunk (default: {DEFAULT_CHUNK_TOKENS}, baseline 500-800)",
    )
    parser.add_argument(
        "--overlap",
        type=float,
        default=DEFAULT_OVERLAP_RATIO,
        help=f"Overlap ratio between chunks (default: {DEFAULT_OVERLAP_RATIO}, baseline 0.10-0.20)",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=None,
        help="Ingest only this file name (repeatable)",
    )
    parser.add_argument("--rebuild", action="store_true", help="Clear the knowledge base first")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Only show chunking results, without embeddings or Supabase",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    directory = Path(args.documents).expanduser() if args.documents else documents_dir()

    if not 50 <= args.chunk_tokens <= 8000:
        print("Error: --chunk-tokens must be between 50 and 8000.")
        return 1
    if not 0.0 <= args.overlap <= 0.5:
        print("Error: --overlap must be between 0.0 and 0.5 (10-20% is the baseline).")
        return 1

    if args.preview:
        return _preview(directory, args.chunk_tokens, args.overlap)

    try:
        from chat_app.presentation.composition import build_retriever
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Error: {exc}")
        return 1

    retriever, warning = build_retriever()
    if retriever is None:
        print(f"Error: {warning}")
        print("Fix the environment variables in .env and run the ingestion again.")
        return 1

    print(f"Knowledge base: {retriever.describe()}")
    print(f"Documents folder: {directory}\n")

    reports = ingest_directory(
        directory,
        embedder=retriever.embedder,
        vector_store=retriever.vector_store,
        chunk_tokens=args.chunk_tokens,
        overlap_ratio=args.overlap,
        rebuild=args.rebuild,
        only=args.only,
    )

    failures = 0
    for report in reports:
        if report.error:
            failures += 1
            print(f"[error]  {report.document}: {report.error}")
        elif report.skipped:
            print(f"[skipped] {report.document}: {report.skipped}")
        else:
            print(
                f"[ok]     {report.document}: {report.chunks} chunks, "
                f"~{report.tokens} tokens, source {', '.join(report.sources)}"
            )

    total_chunks = sum(report.chunks for report in reports if not report.error)
    print(f"\nDone. {total_chunks} chunks stored. Total documents: {len(reports)}.")
    if failures:
        print(f"{failures} document(s) failed. Nothing else was interrupted.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
