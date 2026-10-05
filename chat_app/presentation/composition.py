from chat_app.application.chat_session import ChatSession
from chat_app.application.prompt_design import AdaptivePromptDesigner
from chat_app.infrastructure.config import resolve_provider_config
from chat_app.infrastructure.providers import create_provider
from chat_app.infrastructure.skill_manager import get_skill_system_prompt


def create_chat_session(**options) -> ChatSession:
    """Conecta casos de uso con los adaptadores concretos."""
    return ChatSession(
        resolve_config=resolve_provider_config,
        provider_factory=create_provider,
        load_skill_prompt=get_skill_system_prompt,
        prompt_designer=AdaptivePromptDesigner(),
        **options,
    )