from __future__ import annotations

from typing import Optional

from chat_app.application.prompt_design import PromptDesigner
from chat_app.domain.models import ChatMessage
from chat_app.domain.ports import (
    ProviderConfigResolver,
    ProviderFactory,
    SkillPromptLoader,
)


def _trim_history(history: list[ChatMessage], max_messages: int) -> list[ChatMessage]:
    """Conserva los últimos turnos completos dentro del límite configurado."""
    if max_messages < 2:
        return []
    max_messages -= max_messages % 2
    return history[-max_messages:]


class ChatSession:
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
        history_limit: int = 20,
    ) -> None:
        self.provider_name = provider_name
        self.model = model
        self.skill_name = skill_name
        self.max_tokens = max_tokens
        self.history_limit = history_limit
        self.history: list[ChatMessage] = []
        self._resolve_config = resolve_config
        self._provider_factory = provider_factory
        self._load_skill_prompt = load_skill_prompt
        self._prompt_designer = prompt_designer
        self._providers = {}

    def reset(self) -> None:
        self.history.clear()

    def ask(self, prompt: str) -> str:
        config = self._resolve_config(self.provider_name, self.model)
        key = (config.provider, config.api_key, config.base_url, config.model)
        provider = self._providers.get(key)
        if provider is None:
            provider = self._provider_factory(config)
            self._providers[key] = provider

        skill_instructions = (
            self._load_skill_prompt(self.skill_name) if self.skill_name else None
        )
        system_prompt = self._prompt_designer.build(skill_instructions)
        previous_history = _trim_history(self.history, self.history_limit - 2)
        messages = [*previous_history, {"role": "user", "content": prompt}]
        answer = provider.complete(
            messages,
            system_prompt=system_prompt,
            max_tokens=self.max_tokens,
        )
        self.history = _trim_history(
            [*messages, {"role": "assistant", "content": answer}],
            self.history_limit,
        )
        return answer