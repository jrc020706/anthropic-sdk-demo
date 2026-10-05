from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from chat_app.domain.models import ProviderConfig

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOCUMENTS_DIR = PROJECT_ROOT / "data" / "documents"


class ConfigurationError(ValueError):
    """Raised when the configuration is missing or invalid."""


DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5",
    "openai": "gpt-4o-mini",
}
SUPPORTED_PROVIDERS = tuple(DEFAULT_MODELS)


def default_model(provider: str) -> str:
    """Returns the default model of a known provider."""
    normalized = provider.strip().lower()
    try:
        return DEFAULT_MODELS[normalized]
    except KeyError as exc:
        choices = ", ".join(SUPPORTED_PROVIDERS)
        raise ConfigurationError(
            f"Unsupported provider '{provider}'. Choose one of: {choices}."
        ) from exc


def _optional_url(variable: str) -> Optional[str]:
    value = os.getenv(variable, "").strip()
    return value.rstrip("/") or None


def resolve_provider_config(
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> ProviderConfig:
    """Reads and validates the configuration of the requested provider."""
    selected = (provider or os.getenv("CHAT_PROVIDER", "anthropic")).strip().lower()
    if selected not in SUPPORTED_PROVIDERS:
        choices = ", ".join(SUPPORTED_PROVIDERS)
        raise ConfigurationError(
            f"CHAT_PROVIDER must be one of: {choices}; received '{selected}'."
        )

    env_prefix = selected.upper()
    api_key = os.getenv(f"{env_prefix}_API_KEY", "").strip()
    if not api_key:
        raise ConfigurationError(
            f"Missing {env_prefix}_API_KEY. Add it to the .env file to use {selected}."
        )

    selected_model = (model or os.getenv(f"{env_prefix}_MODEL") or default_model(selected)).strip()
    if not selected_model:
        raise ConfigurationError("The model name cannot be empty.")

    return ProviderConfig(
        provider=selected,
        api_key=api_key,
        base_url=_optional_url(f"{env_prefix}_BASE_URL"),
        model=selected_model,
    )


def documents_dir() -> Path:
    """Folder that holds the local knowledge-base documents."""
    raw = os.getenv("DOCUMENTS_DIR", "").strip()
    path = Path(raw).expanduser() if raw else DEFAULT_DOCUMENTS_DIR
    return path if path.is_absolute() else PROJECT_ROOT / path
