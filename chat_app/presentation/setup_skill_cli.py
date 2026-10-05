from chat_app.infrastructure.skill_manager import list_skills


def main() -> None:
    print("=== Configuración y Verificación de Skills ===\n")
    skills = list_skills()
    if not skills:
        print("No se encontraron skills en el directorio 'skills/'.")
        return
    print(f"Se encontraron {len(skills)} skill(s) locales:")
    for skill in skills:
        print(f"  - [{skill['name']}]: {skill['description']}")
        print(f"    Ruta: {skill['file_path']}")
    print("\nLas skills locales se cargan como instrucciones de sistema.")
    print("  Chat: python main.py --skill <nombre-de-skill>")
    print("  Consulta puntual: python run_skill.py --skill <nombre-de-skill> --prompt <tu-consulta>")