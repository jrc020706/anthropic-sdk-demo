from __future__ import annotations

from typing import Callable, Optional, Protocol, Sequence

from chat_app.domain.models import ChatMessage, ProviderConfig


class ChatProvider(Protocol):
    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        system_prompt: Optional[str],
        max_tokens: int,
    ) -> str:
        """Genera una respuesta de texto."""


ProviderConfigResolver = Callable[[Optional[str], Optional[str]], ProviderConfig]
ProviderFactory = Callable[[ProviderConfig], ChatProvider]
SkillPromptLoader = Callable[[str], str]