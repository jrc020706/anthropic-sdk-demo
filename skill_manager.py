"""Compatibilidad de imports para las skills locales."""

from chat_app.infrastructure.skill_manager import (
    BASE_DIR,
    SKILLS_DIR,
    SKILL_NAME_PATTERN,
    create_skill,
    get_skill_system_prompt,
    list_skills,
    load_skill,
    parse_skill_markdown,
    validate_skill_name,
)

__all__ = [
    "BASE_DIR",
    "SKILLS_DIR",
    "SKILL_NAME_PATTERN",
    "create_skill",
    "get_skill_system_prompt",
    "list_skills",
    "load_skill",
    "parse_skill_markdown",
    "validate_skill_name",
]