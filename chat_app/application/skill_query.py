from chat_app.application.prompt_design import AdaptivePromptDesigner
from chat_app.domain.models import ProviderConfig
from chat_app.domain.ports import (
    ProviderFactory,
    SkillPromptLoader,
)


def run_skill_query(
    skill_name: str,
    user_prompt: str,
    *,
    config: ProviderConfig,
    provider_factory: ProviderFactory,
    load_skill_prompt: SkillPromptLoader,
    max_tokens: int = 1000,
) -> str:
    skill_instructions = load_skill_prompt(skill_name)
    client = provider_factory(config)
    system_prompt = AdaptivePromptDesigner().build(skill_instructions)
    return client.complete(
        [{"role": "user", "content": user_prompt}],
        system_prompt=system_prompt,
        max_tokens=max_tokens,
    )