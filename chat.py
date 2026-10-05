"""Fachada compatible para el chat interactivo."""

from typing import Optional

from chat_app.application.chat_session import ChatSession as _ChatSession
from chat_app.application.prompt_design import AdaptivePromptDesigner
from chat_app.infrastructure.config import resolve_provider_config
from chat_app.infrastructure.providers import create_provider
from chat_app.infrastructure.skill_manager import get_skill_system_prompt
from chat_app.presentation.chat_cli import TerminalChat, main


class ChatSession(_ChatSession):
    def __init__(
        self,
        provider_name: str = "anthropic",
        model: Optional[str] = None,
        skill_name: Optional[str] = None,
        max_tokens: int = 1000,
        history_limit: int = 20,
    ) -> None:
        super().__init__(
            resolve_config=resolve_provider_config,
            provider_factory=create_provider,
            load_skill_prompt=get_skill_system_prompt,
            prompt_designer=AdaptivePromptDesigner(),
            provider_name=provider_name,
            model=model,
            skill_name=skill_name,
            max_tokens=max_tokens,
            history_limit=history_limit,
        )


__all__ = ["ChatSession", "TerminalChat", "main"]