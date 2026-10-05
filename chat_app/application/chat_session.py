from __future__ import annotations

from typing import List, Optional, Sequence

from chat_app.application.prompt_design import PromptDesigner
from chat_app.domain.models import ChatMessage, RetrievedChunk, SessionSummary
from chat_app.domain.ports import (
    ProviderConfigResolver,
    ProviderFactory,
    Retriever,
    SessionStore,
    SkillPromptLoader,
)

DEFAULT_HISTORY_LIMIT = 10  # rolling window required by the acceptance criteria


def _trim_history(history: Sequence[ChatMessage], max_messages: int) -> list[ChatMessage]:
    """Keeps only the most recent whole turns inside the configured limit."""
    if max_messages < 2:
        return []
    max_messages -= max_messages % 2
    return list(history[-max_messages:])


class ChatSession:
    """Conversation use case: provider call + 10-message window + RAG + storage."""

    def __init__(
        self,
        *,
        resolve_config: ProviderConfigResolver,
        provider_factory: ProviderFactory,
        load_skill_prompt: SkillPromptLoader,
        prompt_designer: PromptDesigner,
        provider_name: str = "anthropic",
        model: Optional[str] = None,
        skill_name: Optional[str] = None,
        max_tokens: int = 1000,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
        session_store: Optional[SessionStore] = None,
        retriever: Optional[Retriever] = None,
        session_id: Optional[str] = None,
    ) -> None:
        if history_limit % 2:
            history_limit -= 1
        self.provider_name = provider_name
        self.model = model
        self.skill_name = skill_name
        self.max_tokens = max_tokens
        self.history_limit = max(history_limit, 2)
        self.history: List[ChatMessage] = []
        self.session_id: Optional[str] = session_id
        self.retriever = retriever
        self.last_chunks: List[RetrievedChunk] = []
        self.last_retrieval_error: Optional[str] = None
        self.persistence_error: Optional[str] = None
        self._resolve_config = resolve_config
        self._provider_factory = provider_factory
        self._load_skill_prompt = load_skill_prompt
        self._prompt_designer = prompt_designer
        self._session_store = session_store
        self._providers: dict = {}

    # -- lifecycle --------------------------------------------------------
    @property
    def store(self) -> Optional[SessionStore]:
        return self._session_store

    def reset(self) -> None:
        """Starts a fresh conversation (the previous one is already stored)."""
        self.history.clear()
        self.session_id = None
        self.last_chunks = []
        self.last_retrieval_error = None

    def resume(self, session_id: str) -> tuple[bool, str]:
        """Rebuilds the active context from a saved session's last messages."""
        if not self._session_store:
            return False, "Session storage is not available."
        session_id = session_id.strip().lower()
        if not session_id:
            return False, "Usage: /resume <session-id>"
        try:
            if not self._session_store.exists(session_id):
                return False, f"Unknown session id '{session_id}'. Use /chats to list saved chats."
            messages = self._session_store.load_messages(session_id)
            summary = next(
                (item for item in self._session_store.list_sessions() if item.id == session_id),
                None,
            )
        except Exception as exc:
            return False, f"Could not resume the session: {exc}"

        if not messages:
            return False, f"Session '{session_id}' has no messages yet."

        self.session_id = session_id
        self.history = _trim_history(messages, self.history_limit)
        self.last_chunks = []
        self.last_retrieval_error = None
        if summary:
            self.provider_name = summary.provider or self.provider_name
            self.model = summary.model or None
        loaded = len(self.history)
        return True, (
            f"Resumed session {session_id} with {len(messages)} stored messages; "
            f"active context rebuilt from the last {loaded}."
        )

    # -- inspection -------------------------------------------------------
    def memory_window(self) -> List[ChatMessage]:
        """Returns the messages that will be sent to the provider."""
        return list(self.history)

    def list_chats(self) -> List[SessionSummary]:
        if not self._session_store:
            return []
        return self._session_store.list_sessions()

    # -- main flow --------------------------------------------------------
    def ask(self, prompt: str) -> str:
        chunks, retrieval_error = self._retrieve(prompt)
        self.last_chunks = chunks
        self.last_retrieval_error = retrieval_error

        config = self._resolve_config(self.provider_name, self.model)
        provider = self._provider_for(config)

        skill_instructions = (
            self._load_skill_prompt(self.skill_name) if self.skill_name else None
        )
        system_prompt = self._prompt_designer.build(skill_instructions, chunks)

        # Only the rolling window (plus the current user turn) is sent.
        window = _trim_history(self.history, self.history_limit - 2)
        messages = [*window, {"role": "user", "content": prompt}]
        answer = provider.complete(
            messages,
            system_prompt=system_prompt,
            max_tokens=self.max_tokens,
        )

        updated = _trim_history(
            [*messages, {"role": "assistant", "content": answer}],
            self.history_limit,
        )
        self.history = updated
        self._persist(prompt, answer)
        return answer

    def _provider_for(self, config):
        key = (config.provider, config.api_key, config.base_url, config.model)
        provider = self._providers.get(key)
        if provider is None:
            provider = self._provider_factory(config)
            self._providers[key] = provider
        return provider

    def _retrieve(self, prompt: str) -> tuple[list[RetrievedChunk], Optional[str]]:
        """Runs retrieval before generation; failures never break the chat."""
        if self.retriever is None:
            return [], None
        try:
            return self.retriever.retrieve(prompt), None
        except Exception as exc:
            return [], str(exc)

    def _persist(self, user_message: str, answer: str) -> None:
        """Saves both turns back to the active session."""
        if not self._session_store:
            return
        try:
            if not self.session_id:
                model = self.model or ""
                self.session_id = self._session_store.create_session(
                    self.provider_name, model
                )
                self._session_store.set_title(self.session_id, user_message)
            self._session_store.append(self.session_id, "user", user_message)
            self._session_store.append(self.session_id, "assistant", answer)
            self.persistence_error = None
        except Exception as exc:
            # Recoverable: the chat keeps working even if storage fails.
            self.persistence_error = str(exc)
