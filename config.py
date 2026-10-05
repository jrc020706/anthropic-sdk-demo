"""Import-compatible facade for the project configuration."""

from chat_app.domain.models import ProviderConfig
from chat_app.infrastructure.config import (
    DEFAULT_MODELS,
    SUPPORTED_PROVIDERS,
    ConfigurationError,
    default_model,
    documents_dir,
    resolve_provider_config,
)

__all__ = [
    "ProviderConfig",
    "DEFAULT_MODELS",
    "SUPPORTED_PROVIDERS",
    "ConfigurationError",
    "default_model",
    "documents_dir",
    "resolve_provider_config",
]
