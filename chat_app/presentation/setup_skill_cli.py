from chat_app.infrastructure.skill_manager import list_skills


def main() -> None:
    print("=== Skill Setup and Check ===\n")
    skills = list_skills()
    if not skills:
        print("No skills were found in the 'skills/' directory.")
        return
    print(f"Found {len(skills)} local skill(s):")
    for skill in skills:
        print(f"  - [{skill['name']}]: {skill['description']}")
        print(f"    Path: {skill['file_path']}")
    print("\nLocal skills are loaded as system instructions.")
    print("  Chat: python main.py --skill <skill-name>")
    print("  One-off query: python run_skill.py --skill <skill-name> --prompt <your-question>")
