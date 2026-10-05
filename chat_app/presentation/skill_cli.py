import argparse

from chat_app.application.skill_query import run_skill_query
from chat_app.infrastructure.config import SUPPORTED_PROVIDERS, resolve_provider_config
from chat_app.infrastructure.providers import create_provider
from chat_app.infrastructure.skill_manager import get_skill_system_prompt, list_skills


def run_with_skill(
    skill_name: str,
    user_prompt: str,
    provider: str | None = None,
    model: str | None = None,
    max_tokens: int = 1000,
) -> str:
    config = resolve_provider_config(provider, model)
    print(f"--- Ejecutando con Skill: [{skill_name}] ---")
    print(f"Proveedor: {config.provider}")
    print(f"Modelo: {config.model}")
    print(f"Pregunta: {user_prompt}\n")
    return run_skill_query(
        skill_name,
        user_prompt,
        config=config,
        provider_factory=create_provider,
        load_skill_prompt=get_skill_system_prompt,
        max_tokens=max_tokens,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecutar consultas usando Skills especializadas.")
    parser.add_argument("--skill", "-s", type=str, help="Nombre de la skill a utilizar")
    parser.add_argument("--prompt", "-p", type=str, help="Mensaje o consulta para el modelo")
    parser.add_argument("--provider", choices=SUPPORTED_PROVIDERS, help="Proveedor a utilizar")
    parser.add_argument("--model", "-m", type=str, help="Modelo a utilizar")
    parser.add_argument("--max-tokens", type=int, default=1000, help="Máximo de tokens de salida")
    parser.add_argument("--list", "-l", action="store_true", help="Listar todas las skills disponibles")
    args = parser.parse_args()

    if args.max_tokens < 1:
        parser.error("--max-tokens debe ser positivo.")

    skills = list_skills()
    if args.list:
        print("\nSkills disponibles en el proyecto:")
        for skill in skills:
            print(f"  - {skill['name']}: {skill['description']}")
        print()
        return

    selected_skill = args.skill
    if not selected_skill:
        if not skills:
            print("No se encontraron skills en la carpeta 'skills/'.")
            return
        print("\nSelecciona una Skill:")
        for index, skill in enumerate(skills, start=1):
            print(f"  [{index}] {skill['name']} - {skill['description']}")
        choice = input(f"\nIngresa el número (1-{len(skills)}): ").strip()
        try:
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(skills):
                selected_skill = skills[choice_index]["name"]
            else:
                print("Opción inválida.")
                return
        except ValueError:
            print("Entrada inválida.")
            return

    prompt = args.prompt or input("\nIngresa tu consulta para la Skill: ").strip()
    if not prompt:
        print("Consulta vacía. Cancelando.")
        return

    try:
        print("\nRespuesta:\n")
        print(run_with_skill(
            skill_name=selected_skill,
            user_prompt=prompt,
            provider=args.provider,
            model=args.model,
            max_tokens=args.max_tokens,
        ))
    except Exception as exc:
        print(f"\nError al ejecutar la skill: {exc}")