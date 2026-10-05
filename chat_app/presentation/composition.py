from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from chat_app.application.chat_session import ChatSession
from chat_app.application.prompt_design import AdaptivePromptDesigner
from chat_app.infrastructure.config import ConfigurationError, resolve_provider_config
from chat_app.infrastructure.providers import create_provider
from chat_app.infrastructure.rag import (
    EmbeddingError,
    KnowledgeBaseRetriever,
    OpenAIEmbedder,
    SupabaseVectorStore,
    VectorStoreError,
)
from chat_app.infrastructure.session_store import (
    SessionStoreError,
    SQLiteSessionStore,
    create_session_store,
)
from chat_app.infrastructure.skill_manager import get_skill_system_prompt


@dataclass
class ChatBootstrap:
    """Session plus any recoverable startup problem, shown as a warning."""

    session: ChatSession
    warnings: List[str] = field(default_factory=list)


def build_session_store() -> Tuple[Optional[SQLiteSessionStore], Optional[str]]:
    """Creates the SQLite store; a failure degrades to an in-memory chat."""
    try:
        return create_session_store(), None
    except SessionStoreError as exc:
        return None, str(exc)


def build_retriever() -> Tuple[Optional[KnowledgeBaseRetriever], Optional[str]]:
    """Creates the RAG retriever; a failure degrades to a chat without RAG."""
    try:
        embedder = OpenAIEmbedder()
    except EmbeddingError as exc:
        return None, str(exc)
    try:
        vector_store = SupabaseVectorStore()
    except VectorStoreError as exc:
        return None, str(exc)
    return KnowledgeBaseRetriever.from_env(embedder, vector_store), None


def describe_rag_status() -> str:
    """Human readable knowledge-base status for the ``/rag`` command."""
    retriever, warning = build_retriever()
    if retriever is None:
        return f"Knowledge base unavailable: {warning}"
    return retriever.describe()


def bootstrap_chat_session(**options) -> ChatBootstrap:
    """Wires the session with persistence and RAG, collecting warnings."""
    warnings: List[str] = []

    store, store_warning = build_session_store()
    if store_warning:
        warnings.append(f"{store_warning} Saved chats are disabled for this run.")

    retriever, retriever_warning = build_retriever()
    if retriever_warning:
        warnings.append(f"{retriever_warning} Answers will not use the knowledge base.")

    try:
        resolve_provider_config(options.get("provider_name"), options.get("model"))
    except ConfigurationError as exc:
        warnings.append(
            f"{exc} The chat starts anyway and will ask you to fix it on the first message."
        )

    session = ChatSession(
        resolve_config=resolve_provider_config,
        provider_factory=create_provider,
        load_skill_prompt=get_skill_system_prompt,
        prompt_designer=AdaptivePromptDesigner(),
        session_store=store,
        retriever=retriever,
        **options,
    )
    return ChatBootstrap(session=session, warnings=warnings)


def create_chat_session(**options) -> ChatSession:
    """Backwards compatible factory: the session without startup warnings."""
    return bootstrap_chat_session(**options).session
