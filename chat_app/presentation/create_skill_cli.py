import argparse

from chat_app.infrastructure.skill_manager import create_skill


def interactive_create() -> None:
    print("=== Creador Interactivo de Skills ===\n")
    name = input("Nombre de la Skill (kebab-case, ej: sql-expert): ").strip().lower()
    if not name:
        print("El nombre es obligatorio.")
        return
    description = input("Descripción breve (qué hace y cuándo usarla): ").strip()
    if not description:
        print("La descripción es obligatoria.")
        return
    objective = input("Objetivo principal de la Skill: ").strip()
    if not objective:
        objective = f"Asistir al usuario en tareas relacionadas con {name}."

    print("\nIngresa las reglas o directrices (una por línea). Presiona Enter con línea vacía para terminar:")
    rules = []
    while True:
        rule = input(f"  Regla {len(rules) + 1}: ").strip()
        if not rule:
            break
        rules.append(rule)
    if not rules:
        rules = ["Proporcionar respuestas claras, correctas y profesionales."]

    try:
        file_path = create_skill(name, description, objective, rules)
    except (ValueError, FileExistsError) as exc:
        print(f"Error: {exc}")
        return
    print(f"\nSkill '{name}' creada con éxito en:\n  {file_path}")
    print(f"\nPuedes probarla ejecutando:\n  python run_skill.py --skill {name} --prompt 'Tu pregunta'")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crear una nueva Skill para el proyecto.")
    parser.add_argument("--name", "-n", type=str, help="Nombre de la skill (kebab-case)")
    parser.add_argument("--desc", "-d", type=str, help="Descripción breve de la skill")
    parser.add_argument("--objective", "-o", type=str, help="Objetivo principal")
    parser.add_argument("--rule", "-r", action="append", help="Regla para la skill (puede repetirse)")
    args = parser.parse_args()

    if not args.name:
        interactive_create()
        return
    name = args.name.strip().lower()
    description = (args.desc or f"Especialista en {name}").strip()
    objective = (args.objective or f"Asistir al usuario en tareas relacionadas con {name}.").strip()
    rules = args.rule or ["Proporcionar respuestas claras, correctas y profesionales."]
    try:
        file_path = create_skill(name, description, objective, rules)
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    print(f"Skill '{name}' creada exitosamente en: {file_path}")