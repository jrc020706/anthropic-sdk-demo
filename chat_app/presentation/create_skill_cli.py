import argparse

from chat_app.infrastructure.skill_manager import create_skill


def interactive_create() -> None:
    print("=== Interactive Skill Creator ===\n")
    name = input("Skill name (kebab-case, e.g. sql-expert): ").strip().lower()
    if not name:
        print("The name is required.")
        return
    description = input("Short description (what it does and when to use it): ").strip()
    if not description:
        print("The description is required.")
        return
    objective = input("Main purpose of the skill: ").strip()
    if not objective:
        objective = f"Help the user with tasks related to {name}."

    print("\n Enter the rules, one per line. Press Enter on an empty line to finish:")
    rules = []
    while True:
        rule = input(f"  Rule {len(rules) + 1}: ").strip()
        if not rule:
            break
        rules.append(rule)
    if not rules:
        rules = ["Provide clear, correct and professional answers."]

    try:
        file_path = create_skill(name, description, objective, rules)
    except (ValueError, FileExistsError) as exc:
        print(f"Error: {exc}")
        return
    print(f"\nSkill '{name}' created at:\n  {file_path}")
    print(f"\nTry it with:\n  python run_skill.py --skill {name} --prompt 'Your question'")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new skill for the project.")
    parser.add_argument("--name", "-n", type=str, help="Skill name (kebab-case)")
    parser.add_argument("--desc", "-d", type=str, help="Short description")
    parser.add_argument("--objective", "-o", type=str, help="Main purpose")
    parser.add_argument("--rule", "-r", action="append", help="Rule for the skill (repeatable)")
    args = parser.parse_args()

    if not args.name:
        interactive_create()
        return
    name = args.name.strip().lower()
    description = (args.desc or f"Specialist in {name}").strip()
    objective = (args.objective or f"Help the user with tasks related to {name}.").strip()
    rules = args.rule or ["Provide clear, correct and professional answers."]
    try:
        file_path = create_skill(name, description, objective, rules)
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    print(f"Skill '{name}' created at: {file_path}")
