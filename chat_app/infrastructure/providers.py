from __future__ import annotations

from typing import Optional, Sequence

from chat_app.domain.models import ChatMessage, ProviderConfig
from chat_app.domain.ports import ChatProvider


class ProviderError(RuntimeError):
    """Error recuperable al solicitar una respuesta a un proveedor."""


class AnthropicProvider:
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
            raise ProviderError(f"No se pudo obtener respuesta de Anthropic: {exc}") from exc

        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        if not text:
            raise ProviderError("Anthropic no devolvió contenido de texto.")
        return text


class OpenAIProvider:
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
            raise ProviderError(f"No se pudo obtener respuesta de OpenAI: {exc}") from exc

        text = response.choices[0].message.content if response.choices else None
        if not text:
            raise ProviderError("OpenAI no devolvió contenido de texto.")
        return text


def create_provider(config: ProviderConfig) -> ChatProvider:
    """Crea el adaptador apropiado para la configuración resuelta."""
    if config.provider == "anthropic":
        return AnthropicProvider(config)
    if config.provider == "openai":
        return OpenAIProvider(config)
    raise ProviderError(f"No existe adaptador para el proveedor '{config.provider}'.")