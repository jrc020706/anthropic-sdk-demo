from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    api_key: str
    base_url: Optional[str]
    model: str


@dataclass(frozen=True)
class RetrievedChunk:
    """A knowledge-base fragment returned by the retriever."""

    content: str
    source: str
    score: float
    chunk_index: int = 0

    def as_context_block(self) -> str:
        """Formats the chunk so the model can cite ``source`` in its answer."""
        return f"[source: {self.source} | chunk: {self.chunk_index} | relevance: {self.score:.3f}]\n{self.content}"


@dataclass(frozen=True)
class SessionSummary:
    """Metadata of a chat session persisted on disk."""

    id: str
    provider: str
    model: str
    message_count: int
    created_at: str
    updated_at: str
    title: str = ""


@dataclass
class IngestionReport:
    """Outcome of a document ingestion run."""

    document: str
    chunks: int = 0
    tokens: int = 0
    skipped: str = ""
    error: str = ""
    sources: list[str] = field(default_factory=list)
