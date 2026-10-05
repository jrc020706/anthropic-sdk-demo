from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parents[2]
SKILLS_DIR = BASE_DIR / "skills"
SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_skill_name(name: str) -> str:
    """Validates portable names and blocks paths outside ``skills/``."""
    normalized = name.strip().lower()
    if not SKILL_NAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Skill names must be kebab-case: lowercase letters, digits and single hyphens."
        )
    return normalized


def parse_skill_markdown(content: str) -> Dict[str, Any]:
    """Parses the basic frontmatter and instructions of a skill file."""
    frontmatter: Dict[str, str] = {}
    body = content
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if match:
        raw_frontmatter = match.group(1)
        body = match.group(2).strip()
        for line in raw_frontmatter.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                frontmatter[key.strip()] = value.strip().strip("\"'")

    return {
        "metadata": frontmatter,
        "name": frontmatter.get("name", ""),
        "description": frontmatter.get("description", ""),
        "instructions": body,
    }


def list_skills(skills_dir: Path = SKILLS_DIR) -> List[Dict[str, Any]]:
    """Lists local skills that contain a ``SKILL.md`` file."""
    if not skills_dir.exists():
        return []

    skills = []
    for item in sorted(skills_dir.iterdir()):
        if item.is_dir():
            skill_file = item / "SKILL.md"
            if skill_file.exists():
                try:
                    data = parse_skill_markdown(skill_file.read_text(encoding="utf-8"))
                    data["dir_name"] = item.name
                    data["file_path"] = str(skill_file)
                    skills.append(data)
                except Exception as exc:
                    skills.append(
                        {
                            "dir_name": item.name,
                            "file_path": str(skill_file),
                            "name": item.name,
                            "error": str(exc),
                        }
                    )
    return skills


def load_skill(name_or_dir: str, skills_dir: Path = SKILLS_DIR) -> Optional[Dict[str, Any]]:
    """Loads a skill by its name or by its directory name."""
    for skill in list_skills(skills_dir):
        if skill.get("name") == name_or_dir or skill.get("dir_name") == name_or_dir:
            return skill
    return None


def get_skill_system_prompt(name_or_dir: str, skills_dir: Path = SKILLS_DIR) -> str:
    """Builds the system instructions for a local skill."""
    skill = load_skill(name_or_dir, skills_dir)
    if not skill:
        raise ValueError(f"Skill '{name_or_dir}' not found in {skills_dir}")

    instructions = skill.get("instructions", "")
    name = skill.get("name") or skill.get("dir_name")
    description = skill.get("description", "")
    system_prompt = f"You are a specialist running the '{name}' skill.\n"
    if description:
        system_prompt += f"Skill purpose: {description}\n\n"
    system_prompt += "Follow these guidelines and rules strictly:\n"
    return system_prompt + instructions


def create_skill(
    name: str,
    description: str,
    objective: str,
    rules: List[str],
    skills_dir: Path = SKILLS_DIR,
) -> Path:
    """Creates a local skill written as Markdown."""
    name = validate_skill_name(name)
    skill_folder = skills_dir / name
    skill_file = skill_folder / "SKILL.md"
    if skill_file.exists():
        raise FileExistsError(
            f"A skill named '{name}' already exists. Choose another name to avoid overwriting it."
        )

    skill_folder.mkdir(parents=True, exist_ok=True)
    rules_formatted = "\n".join(f"{index + 1}. {rule}" for index, rule in enumerate(rules))
    content = f"""---
name: {name}
description: {description}
---

# {name.replace('-', ' ').title()}

## Purpose

{objective}

## Instructions

{rules_formatted}
"""
    skill_file.write_text(content, encoding="utf-8")
    return skill_file
