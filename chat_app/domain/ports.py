from __future__ import annotations

from typing import Callable, Optional, Protocol, Sequence

from chat_app.domain.models import (
    ChatMessage,
    ProviderConfig,
    RetrievedChunk,
    SessionSummary,
)


class ChatProvider(Protocol):
    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        system_prompt: Optional[str],
        max_tokens: int,
    ) -> str:
        """Generates a text reply for the given conversation."""


class SessionStore(Protocol):
    """Persists complete chat sessions across application restarts."""

    def create_session(self, provider: str, model: str) -> str:
        """Creates an empty session and returns its stable ID."""

    def append(self, session_id: str, role: str, content: str) -> None:
        """Appends one message to a session."""

    def list_sessions(self) -> list[SessionSummary]:
        """Lists saved sessions, newest first, ordered by stable ID metadata."""

    def load_messages(self, session_id: str) -> list[ChatMessage]:
        """Loads the full message history of a session."""

    def exists(self, session_id: str) -> bool:
        """Tells whether a session ID is stored."""

    def set_title(self, session_id: str, title: str) -> None:
        """Stores a short human readable title for the session."""


class Retriever(Protocol):
    """Returns knowledge-base chunks that support the user question."""

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        """Returns the most relevant chunks, empty when nothing matches."""


ProviderConfigResolver = Callable[[Optional[str], Optional[str]], ProviderConfig]
ProviderFactory = Callable[[ProviderConfig], ChatProvider]
SkillPromptLoader = Callable[[str], str]
