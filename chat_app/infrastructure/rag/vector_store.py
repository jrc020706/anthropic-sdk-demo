from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence

from chat_app.domain.models import RetrievedChunk

DEFAULT_TABLE = "documents"
DEFAULT_DISTANCE_THRESHOLD = 0.20


class VectorStoreError(RuntimeError):
    """Recoverable error while talking to the vector database."""


class SupabaseVectorStore:
    """Hosted Supabase (PostgreSQL + pgvector) store for RAG embeddings."""

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        *,
        table: Optional[str] = None,
    ) -> None:
        self.url = (url or os.getenv("SUPABASE_URL", "")).strip().rstrip("/")
        self.key = (key or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY") or "").strip()
        self.table = (table or os.getenv("SUPABASE_TABLE", DEFAULT_TABLE)).strip() or DEFAULT_TABLE

        if not self.url:
            raise VectorStoreError(
                "SUPABASE_URL is missing. Set it in .env to enable the knowledge base."
            )
        if not self.key:
            raise VectorStoreError(
                "SUPABASE_SERVICE_KEY (or SUPABASE_ANON_KEY) is missing. "
                "Set it in .env to enable the knowledge base."
            )

        try:
            from supabase import create_client
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise VectorStoreError(
                "The 'supabase' package is not installed. Run: pip install -r requirements.txt"
            ) from exc

        try:
            self._client = create_client(self.url, self.key)
        except Exception as exc:
            raise VectorStoreError(f"Could not connect to Supabase: {exc}") from exc

    # -- writes -----------------------------------------------------------
    def add_chunks(
        self,
        *,
        contents: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        metadata: Sequence[Dict[str, Any]],
    ) -> int:
        """Inserts chunks with their embedding and source metadata."""
        if not (len(contents) == len(embeddings) == len(metadata)):
            raise VectorStoreError("contents, embeddings and metadata must have the same length.")

        rows = [
            {
                "content": content,
                "embedding": list(embedding),
                "metadata": dict(meta),
            }
            for content, embedding, meta in zip(contents, embeddings, metadata)
        ]
        try:
            self._client.table(self.table).insert(rows).execute()
        except Exception as exc:
            raise VectorStoreError(
                self._explain_write_error(exc)
            ) from exc
        return len(rows)

    def delete_source(self, source: str) -> int:
        """Removes previously stored chunks of one document (re-ingestion)."""
        try:
            response = (
                self._client.table(self.table)
                .delete()
                .contains("metadata", {"source": source})
                .execute()
            )
        except Exception as exc:
            raise VectorStoreError(f"Could not remove old chunks of '{source}': {exc}") from exc
        return len(response.data or [])

    def clear(self) -> int:
        """Deletes every stored chunk (``--rebuild`` ingestion)."""
        removed = self.count()
        try:
            self._client.table(self.table).delete().neq("id", 0).execute()
        except Exception as exc:
            raise VectorStoreError(f"Could not clear the knowledge base: {exc}") from exc
        return removed

    # -- reads ------------------------------------------------------------
    def count(self) -> int:
        try:
            response = self._client.table(self.table).select("id", count="exact").limit(1).execute()
        except Exception as exc:
            raise VectorStoreError(self._explain_read_error(exc)) from exc
        return int(response.count or 0)

    def search(
        self,
        embedding: Sequence[float],
        top_k: int = 5,
        threshold: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        """Returns the closest chunks, each one carrying its source metadata."""
        try:
            response = self._client.rpc(
                "match_documents",
                {
                    "query_embedding": list(embedding),
                    "match_count": max(1, int(top_k)),
                },
            ).execute()
        except Exception as exc:
            raise VectorStoreError(self._explain_read_error(exc)) from exc

        cutoff = DEFAULT_DISTANCE_THRESHOLD if threshold is None else threshold
        chunks: List[RetrievedChunk] = []
        for row in response.data or []:
            metadata = row.get("metadata") or {}
            score = float(row.get("similarity", 0.0))
            if score < cutoff:
                continue
            chunks.append(
                RetrievedChunk(
                    content=row.get("content", ""),
                    source=str(metadata.get("source") or metadata.get("document") or "unknown"),
                    score=score,
                    chunk_index=int(metadata.get("chunk_index", 0)),
                )
            )
        return chunks

    # -- diagnostics ------------------------------------------------------
    def _explain_write_error(self, exc: Exception) -> str:
        message = str(exc)
        if "relation" in message and "does not exist" in message:
            return (
                f"Table '{self.table}' does not exist in Supabase. "
                "Run data/supabase/schema.sql in the SQL editor first."
            )
        if "column" in message and "embedding" in message:
            return (
                "The 'embedding' column is missing or has the wrong vector dimension. "
                "Run data/supabase/schema.sql in the SQL editor."
            )
        return f"Could not write to the Supabase vector store: {message}"

    def _explain_read_error(self, exc: Exception) -> str:
        message = str(exc)
        if "match_documents" in message:
            return (
                "The 'match_documents' function is missing in Supabase. "
                "Run data/supabase/schema.sql in the SQL editor."
            )
        if "relation" in message and "does not exist" in message:
            return (
                f"Table '{self.table}' does not exist in Supabase. "
                "Run data/supabase/schema.sql in the SQL editor."
            )
        return f"Could not query the Supabase vector store: {message}"


def create_vector_store(**options) -> SupabaseVectorStore:
    """Factory used by the composition root."""
    return SupabaseVectorStore(**options)
