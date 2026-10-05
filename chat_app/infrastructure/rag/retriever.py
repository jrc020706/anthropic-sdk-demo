from __future__ import annotations

import os
from typing import List, Optional

from chat_app.domain.models import RetrievedChunk

DEFAULT_TOP_K = 5  # RAG baseline: top 4-6 chunks


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


class KnowledgeBaseRetriever:
    """Embeds the question and returns supporting chunks from the vector store."""

    def __init__(
        self,
        embedder,
        vector_store,
        *,
        top_k: int = DEFAULT_TOP_K,
        threshold: Optional[float] = None,
    ) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.top_k = top_k
        self.threshold = (
            threshold if threshold is not None else _env_float("RAG_SIMILARITY_THRESHOLD", 0.20)
        )

    @classmethod
    def from_env(cls, embedder, vector_store) -> "KnowledgeBaseRetriever":
        raw_top_k = os.getenv("RAG_TOP_K", "").strip()
        try:
            top_k = int(raw_top_k) if raw_top_k else DEFAULT_TOP_K
        except ValueError:
            top_k = DEFAULT_TOP_K
        return cls(embedder, vector_store, top_k=max(1, min(top_k, 20)))

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[RetrievedChunk]:
        """Returns relevant chunks; an empty list means "not enough information"."""
        cleaned = (query or "").strip()
        if not cleaned:
            return []
        embedding = self.embedder.embed_query(cleaned)
        return self.vector_store.search(
            embedding,
            top_k=self.top_k if top_k is None else top_k,
            threshold=self.threshold,
        )

    def describe(self) -> str:
        """Human readable status used by the ``/rag`` command."""
        try:
            stored = self.vector_store.count()
        except Exception as exc:
            return f"Knowledge base unavailable: {exc}"
        return (
            f"Stored chunks: {stored} | top_k: {self.top_k} | "
            f"min relevance: {self.threshold:.2f} | embedding model: {self.embedder.model}"
        )
