"""Compatibilidad de imports para la configuración del proyecto."""

from chat_app.domain.models import ProviderConfig
from chat_app.infrastructure.config import (
    DEFAULT_MODELS,
    SUPPORTED_PROVIDERS,
    ConfigurationError,
    default_model,
    resolve_provider_config,
)

__all__ = [
    "ProviderConfig",
    "DEFAULT_MODELS",
    "SUPPORTED_PROVIDERS",
    "ConfigurationError",
    "default_model",
    "resolve_provider_config",
]