from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

from chat_app.domain.models import ProviderConfig

load_dotenv()


class ConfigurationError(ValueError):
    """Señala una configuración incompleta o no válida."""


DEFAULT_MODELS = {
    "anthropic": "auto/best-coding",
    "openai": "gpt-4o-mini",
}
SUPPORTED_PROVIDERS = tuple(DEFAULT_MODELS)


def default_model(provider: str) -> str:
    """Obtiene el modelo predeterminado de un proveedor conocido."""
    normalized = provider.strip().lower()
    try:
        return DEFAULT_MODELS[normalized]
    except KeyError as exc:
        choices = ", ".join(SUPPORTED_PROVIDERS)
        raise ConfigurationError(
            f"Proveedor '{provider}' no soportado. Usa uno de: {choices}."
        ) from exc


def _optional_url(variable: str) -> Optional[str]:
    value = os.getenv(variable, "").strip()
    return value.rstrip("/") or None


def resolve_provider_config(
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> ProviderConfig:
    """Lee y valida la configuración del proveedor solicitado."""
    selected = (provider or os.getenv("CHAT_PROVIDER", "anthropic")).strip().lower()
    if selected not in SUPPORTED_PROVIDERS:
        choices = ", ".join(SUPPORTED_PROVIDERS)
        raise ConfigurationError(
            f"CHAT_PROVIDER debe ser uno de: {choices}; se recibió '{selected}'."
        )

    env_prefix = selected.upper()
    api_key = os.getenv(f"{env_prefix}_API_KEY", "").strip()
    if not api_key:
        raise ConfigurationError(
            f"Falta {env_prefix}_API_KEY. Añádela al archivo .env para usar {selected}."
        )

    selected_model = (model or os.getenv(f"{env_prefix}_MODEL") or default_model(selected)).strip()
    if not selected_model:
        raise ConfigurationError("El modelo no puede estar vacío.")

    return ProviderConfig(
        provider=selected,
        api_key=api_key,
        base_url=_optional_url(f"{env_prefix}_BASE_URL"),
        model=selected_model,
    )