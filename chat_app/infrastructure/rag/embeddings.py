from __future__ import annotations

import os
from typing import List, Optional, Sequence

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_DIMENSIONS = 1536
DEFAULT_BATCH_SIZE = 64


class EmbeddingError(RuntimeError):
    """Recoverable error while creating embeddings."""


class OpenAIEmbedder:
    """Wraps the official OpenAI SDK embedding endpoint used by the RAG flow."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
        if not key:
            raise EmbeddingError(
                "RAG is disabled: OPENAI_API_KEY is missing. "
                "Add it to .env to embed documents and queries."
            )
        if batch_size < 1:
            raise EmbeddingError("batch_size must be positive.")

        resolved_base = (base_url or os.getenv("OPENAI_BASE_URL", "")).strip().rstrip("/")
        if resolved_base and not resolved_base.endswith("/v1"):
            resolved_base = f"{resolved_base}/v1"

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise EmbeddingError(
                "The official OpenAI SDK is not installed. Run: pip install -r requirements.txt"
            ) from exc

        try:
            self._client = OpenAI(api_key=key, base_url=resolved_base or None)
        except Exception as exc:
            raise EmbeddingError(f"Could not initialise the OpenAI embedding client: {exc}") from exc

        self.model = (model or os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)).strip()
        raw_dimensions = dimensions or int(
            os.getenv("EMBEDDING_DIMENSIONS", DEFAULT_EMBEDDING_DIMENSIONS)
        )
        self.dimensions = raw_dimensions if raw_dimensions > 0 else DEFAULT_EMBEDDING_DIMENSIONS
        self.batch_size = batch_size

    def embed_documents(self, texts: Sequence[str]) -> List[List[float]]:
        """Embeds many texts in batches, preserving the input order."""
        vectors: List[List[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = list(texts[start : start + self.batch_size])
            vectors.extend(self._embed(batch))
        return vectors

    def embed_query(self, text: str) -> List[float]:
        cleaned = text.strip()
        if not cleaned:
            raise EmbeddingError("Cannot embed an empty query.")
        return self._embed([cleaned])[0]

    def _embed(self, texts: Sequence[str]) -> List[List[float]]:
        payload = {"model": self.model, "input": list(texts)}
        if self.model.startswith("text-embedding-3"):
            payload["dimensions"] = self.dimensions
        try:
            response = self._client.embeddings.create(**payload)
        except Exception as exc:
            raise EmbeddingError(f"Embedding request to OpenAI failed: {exc}") from exc

        data = sorted(response.data, key=lambda item: item.index)
        vectors = [item.embedding for item in data]
        if len(vectors) != len(texts):
            raise EmbeddingError(
                f"OpenAI returned {len(vectors)} embeddings for {len(texts)} inputs."
            )
        return vectors


def create_embedder(**options) -> OpenAIEmbedder:
    """Factory used by the composition root."""
    return OpenAIEmbedder(**options)
