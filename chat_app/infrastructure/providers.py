from __future__ import annotations

from typing import Optional, Sequence

from chat_app.domain.models import ChatMessage, ProviderConfig
from chat_app.domain.ports import ChatProvider


class ProviderError(RuntimeError):
    """Recoverable error returned by a provider adapter."""


class AnthropicProvider:
    """Adapter for the official Anthropic SDK."""

    def __init__(self, config: ProviderConfig) -> None:
        from anthropic import Anthropic

        base_url = config.base_url
        if base_url and base_url.endswith("/v1"):
            base_url = base_url[:-3]

        self.client = Anthropic(api_key=config.api_key, base_url=base_url)
        self.model = config.model

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        system_prompt: Optional[str],
        max_tokens: int,
    ) -> str:
        try:
            request = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": list(messages),
            }
            if system_prompt:
                request["system"] = system_prompt
            response = self.client.messages.create(**request)
        except Exception as exc:
            raise ProviderError(f"Anthropic did not answer: {exc}") from exc

        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        if not text:
            raise ProviderError("Anthropic returned no text content.")
        return text


class OpenAIProvider:
    """Adapter for the official OpenAI SDK.

    Also serves OpenAI-compatible providers such as Groq and OpenRouter, so the
    conversation logic stays in one place for every provider.
    """

    def __init__(self, config: ProviderConfig) -> None:
        from openai import OpenAI

        base_url = config.base_url
        if base_url and not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"

        self.client = OpenAI(api_key=config.api_key, base_url=base_url)
        self.model = config.model

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        system_prompt: Optional[str],
        max_tokens: int,
    ) -> str:
        request_messages: list[ChatMessage] = []
        if system_prompt:
            request_messages.append({"role": "system", "content": system_prompt})
        request_messages.extend(messages)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=request_messages,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            raise ProviderError(f"OpenAI did not answer: {exc}") from exc

        text = response.choices[0].message.content if response.choices else None
        if not text:
            raise ProviderError("OpenAI returned no text content.")
        return text


# OpenAI-compatible providers served by the official OpenAI SDK adapter.
OPENAI_COMPATIBLE_PROVIDERS = ("groq", "openrouter")


def create_provider(config: ProviderConfig) -> ChatProvider:
    """Creates the adapter that matches the resolved configuration."""
    if config.provider == "anthropic":
        return AnthropicProvider(config)
    if config.provider == "openai" or config.provider in OPENAI_COMPATIBLE_PROVIDERS:
        return OpenAIProvider(config)
    raise ProviderError(f"No adapter available for provider '{config.provider}'.")
