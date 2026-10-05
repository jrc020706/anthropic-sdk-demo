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
    print(f"--- Running with skill: [{skill_name}] ---")
    print(f"Provider: {config.provider}")
    print(f"Model: {config.model}")
    print(f"Question: {user_prompt}\n")
    return run_skill_query(
        skill_name,
        user_prompt,
        config=config,
        provider_factory=create_provider,
        load_skill_prompt=get_skill_system_prompt,
        max_tokens=max_tokens,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a one-off query using a skill.")
    parser.add_argument("--skill", "-s", type=str, help="Name of the skill to use")
    parser.add_argument("--prompt", "-p", type=str, help="Question sent to the model")
    parser.add_argument("--provider", choices=SUPPORTED_PROVIDERS, help="Provider to use")
    parser.add_argument("--model", "-m", type=str, help="Model to use")
    parser.add_argument("--max-tokens", type=int, default=1000, help="Maximum output tokens")
    parser.add_argument("--list", "-l", action="store_true", help="List the available skills")
    args = parser.parse_args()

    if args.max_tokens < 1:
        parser.error("--max-tokens must be positive.")

    skills = list_skills()
    if args.list:
        print("\nSkills available in the project:")
        for skill in skills:
            print(f"  - {skill['name']}: {skill['description']}")
        print()
        return

    selected_skill = args.skill
    if not selected_skill:
        if not skills:
            print("No skills were found in the 'skills/' folder.")
            return
        print("\nSelect a skill:")
        for index, skill in enumerate(skills, start=1):
            print(f"  [{index}] {skill['name']} - {skill['description']}")
        choice = input(f"\nEnter the number (1-{len(skills)}): ").strip()
        try:
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(skills):
                selected_skill = skills[choice_index]["name"]
            else:
                print("Invalid option.")
                return
        except ValueError:
            print("Invalid input.")
            return

    prompt = args.prompt or input("\nEnter your question for the skill: ").strip()
    if not prompt:
        print("Empty question. Cancelled.")
        return

    try:
        print("\nAnswer:\n")
        print(run_with_skill(
            skill_name=selected_skill,
            user_prompt=prompt,
            provider=args.provider,
            model=args.model,
            max_tokens=args.max_tokens,
        ))
    except Exception as exc:
        print(f"\nSkill execution failed: {exc}")
