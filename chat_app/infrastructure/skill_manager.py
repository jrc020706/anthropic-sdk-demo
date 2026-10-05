import re
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parents[2]
SKILLS_DIR = BASE_DIR / "skills"
SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_skill_name(name: str) -> str:
    """Valida nombres portables y evita rutas fuera de ``skills/``."""
    normalized = name.strip().lower()
    if not SKILL_NAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "El nombre de la skill debe usar kebab-case: letras minúsculas, "
            "números y guiones simples."
        )
    return normalized


def parse_skill_markdown(content: str) -> Dict[str, Any]:
    """Parsea el frontmatter básico y las instrucciones de un archivo de skill."""
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
    """Lista skills locales que contienen un archivo ``SKILL.md``."""
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
                    skills.append({
                        "dir_name": item.name,
                        "file_path": str(skill_file),
                        "name": item.name,
                        "error": str(exc),
                    })
    return skills


def load_skill(name_or_dir: str, skills_dir: Path = SKILLS_DIR) -> Optional[Dict[str, Any]]:
    """Carga una skill por su nombre o por el nombre de su directorio."""
    for skill in list_skills(skills_dir):
        if skill.get("name") == name_or_dir or skill.get("dir_name") == name_or_dir:
            return skill
    return None


def get_skill_system_prompt(name_or_dir: str, skills_dir: Path = SKILLS_DIR) -> str:
    """Genera las instrucciones de sistema para una skill local."""
    skill = load_skill(name_or_dir, skills_dir)
    if not skill:
        raise ValueError(f"Skill '{name_or_dir}' no encontrada en {skills_dir}")

    instructions = skill.get("instructions", "")
    name = skill.get("name") or skill.get("dir_name")
    description = skill.get("description", "")
    system_prompt = f"Eres un asistente especializado ejecutando la Skill '{name}'.\n"
    if description:
        system_prompt += f"Propósito de la Skill: {description}\n\n"
    system_prompt += "Sigue rigurosamente las siguientes directrices y reglas:\n"
    return system_prompt + instructions


def create_skill(
    name: str,
    description: str,
    objective: str,
    rules: List[str],
    skills_dir: Path = SKILLS_DIR,
) -> Path:
    """Crea una skill local en formato Markdown."""
    name = validate_skill_name(name)
    skill_folder = skills_dir / name
    skill_file = skill_folder / "SKILL.md"
    if skill_file.exists():
        raise FileExistsError(
            f"Ya existe una skill llamada '{name}'. Elige otro nombre para no sobrescribirla."
        )

    skill_folder.mkdir(parents=True, exist_ok=True)
    rules_formatted = "\n".join(f"{index + 1}. {rule}" for index, rule in enumerate(rules))
    content = f"""---
name: {name}
description: {description}
---

# {name.replace('-', ' ').title()}

## Objetivo

{objective}

## Instrucciones

{rules_formatted}
"""
    skill_file.write_text(content, encoding="utf-8")
    return skill_file