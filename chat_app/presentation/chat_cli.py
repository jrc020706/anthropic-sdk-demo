"""Interactive terminal chat with memory, saved chats, RAG and several providers."""

import argparse
import os

from chat_app.application.chat_session import DEFAULT_HISTORY_LIMIT
from chat_app.infrastructure.config import (
    ConfigurationError,
    SUPPORTED_PROVIDERS,
    default_model,
)
from chat_app.infrastructure.providers import ProviderError
from chat_app.infrastructure.session_store import SessionStoreError
from chat_app.infrastructure.skill_manager import list_skills, load_skill
from chat_app.presentation.composition import bootstrap_chat_session, describe_rag_status


HELP = """Commands:
  /help                    Show this help.
  /status                  Show the configuration of the session.
  /providers               List the supported providers.
  /provider <name>         Switch the active provider (see /providers).
  /model <name>            Change the model of the current provider.
  /memory                  Inspect the active 10-message context window.
  /chats                   List saved sessions by their stable id.
  /resume <session-id>     Continue a saved session.
  /skills                  List the available skills.
  /skill <name|none>       Enable a skill or disable it.
  /rag                     Show the knowledge-base (RAG) status.
  /new                     Start a new conversation.
  /exit                    Close the chat.
"""

REQUEST_ERROR = """Request failed: {detail}
Check your .env file (see .env.example) and try again. The chat is still running."""


class TerminalChat:
    def __init__(self, session, warnings=None) -> None:
        self.session = session
        self.warnings = list(warnings or [])

    # -- output helpers ---------------------------------------------------
    def print_status(self) -> None:
        model = self.session.model or default_model(self.session.provider_name)
        skill = self.session.skill_name or "none"
        session_id = self.session.session_id or "not started"
        rag = "on" if self.session.retriever else "off"
        print(
            f"Provider: {self.session.provider_name} | Model: {model} | "
            f"Skill: {skill} | Context messages: {len(self.session.history)}/"
            f"{self.session.history_limit} | Session: {session_id} | RAG: {rag}"
        )

    def _report_turn_notes(self) -> None:
        if self.session.last_chunks:
            seen: list[str] = []
            for chunk in self.session.last_chunks:
                label = f"{chunk.source} ({chunk.score:.2f})"
                if label not in seen:
                    seen.append(label)
            print(f"Sources: {', '.join(seen)}")
        if self.session.last_retrieval_error:
            print(f"RAG warning: {self.session.last_retrieval_error}")
        if self.session.persistence_error:
            print(f"Storage warning: {self.session.persistence_error}")

    # -- commands ---------------------------------------------------------
    def print_memory(self) -> None:
        window = self.session.memory_window()
        limit = self.session.history_limit
        if not window:
            print(
                f"Active context window: 0/{limit} messages. "
                "It is filled as soon as the conversation starts."
            )
            return
        print(f"Active context window: {len(window)}/{limit} messages (oldest first):")
        for index, message in enumerate(window, start=1):
            preview = " ".join(str(message["content"]).split())
            if len(preview) > 90:
                preview = preview[:87] + "..."
            print(f"  {index:>2}. [{message['role']}] {preview}")

    def print_chats(self) -> None:
        sessions = self.session.list_chats()
        if not sessions:
            print("No saved chats yet. Send a message and it will be stored.")
            return
        print(f"Saved sessions ({len(sessions)}):")
        for item in sessions:
            marker = "*" if item.id == self.session.session_id else " "
            title = f' - "{item.title}"' if item.title else ""
            print(
                f" {marker} {item.id} | {item.provider}/{item.model or "default"} | "
                f"{item.message_count} messages | updated {item.updated_at}{title}"
            )
        print("Use /resume <session-id> to continue one. '*' marks the active session.")

    def handle_command(self, command: str) -> bool:
        name, _, argument = command[1:].partition(" ")
        name = name.lower().strip()
        argument = argument.strip()

        if name in {"exit", "quit"}:
            return False
        if name == "help":
            print(HELP)
        elif name == "status":
            self.print_status()
        elif name == "providers":
            print("Supported providers: " + ", ".join(SUPPORTED_PROVIDERS))
        elif name == "provider":
            selected_provider = argument.lower()
            if selected_provider not in SUPPORTED_PROVIDERS:
                print("Available providers: " + ", ".join(SUPPORTED_PROVIDERS))
            else:
                self.session.provider_name = selected_provider
                self.session.model = None
                self.session.reset()
                print(f"Provider switched to {selected_provider}. Started a new conversation.")
        elif name == "model":
            if not argument:
                print("Provide a model name, for example: /model gpt-4o-mini")
            else:
                self.session.model = argument
                print(f"Model switched to {argument}.")
        elif name == "memory":
            self.print_memory()
        elif name == "chats":
            self.print_chats()
        elif name == "resume":
            if not argument:
                print("Usage: /resume <session-id>")
            else:
                ok, message = self.session.resume(argument)
                print(message)
                if ok:
                    self.print_status()
        elif name == "rag":
            print(describe_rag_status())
        elif name == "skills":
            skills = list_skills()
            if skills:
                for skill in skills:
                    print(f"- {skill['name']}: {skill['description']}")
            else:
                print("No skills available.")
        elif name == "skill":
            if argument.lower() in {"none", "off"}:
                self.session.skill_name = None
                self.session.reset()
                print("Skill disabled. Started a new conversation.")
            elif load_skill(argument):
                self.session.skill_name = argument
                self.session.reset()
                print(f"Skill enabled: {argument}. Started a new conversation.")
            else:
                print(f"There is no skill named '{argument}'. Use /skills to list them.")
        elif name == "new":
            self.session.reset()
            print("Started a new conversation.")
        else:
            print("Unknown command. Use /help to see the available commands.")
        return True

    # -- loop -------------------------------------------------------------
    def run(self) -> None:
        print("Multi-provider terminal chat. Type /help to see the commands.")
        for warning in self.warnings:
            print(f"Warning: {warning}")
        self.print_status()

        while True:
            try:
                prompt = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                return

            if not prompt:
                continue
            if prompt.startswith("/"):
                if not self.handle_command(prompt):
                    print("Goodbye.")
                    return
                continue

            try:
                print(f"\nAssistant: {self.session.ask(prompt)}")
            except (ConfigurationError, ProviderError, SessionStoreError, ValueError) as exc:
                print(REQUEST_ERROR.format(detail=exc))
            except KeyboardInterrupt:
                print("\nRequest cancelled. The conversation is still open.")
            self._report_turn_notes()


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-provider terminal chat.")
    parser.add_argument("--provider", choices=SUPPORTED_PROVIDERS, help="Initial provider")
    parser.add_argument("--model", help="Initial model")
    parser.add_argument("--skill", help="Initial skill")
    parser.add_argument("--max-tokens", type=int, default=1000, help="Maximum output tokens")
    parser.add_argument(
        "--history-limit",
        type=int,
        default=DEFAULT_HISTORY_LIMIT,
        help="Messages kept in the active context window",
    )
    args = parser.parse_args()

    provider = args.provider or os.getenv("CHAT_PROVIDER", "anthropic").strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        parser.error("CHAT_PROVIDER must be one of: " + ", ".join(SUPPORTED_PROVIDERS))
    if args.skill and not load_skill(args.skill):
        parser.error(f"There is no skill named '{args.skill}'.")
    if args.max_tokens < 1 or args.history_limit < 2:
        parser.error("--max-tokens must be positive and --history-limit must be at least 2.")

    bootstrap = bootstrap_chat_session(
        provider_name=provider,
        model=args.model or os.getenv("CHAT_MODEL"),
        skill_name=args.skill,
        max_tokens=args.max_tokens,
        history_limit=args.history_limit,
    )
    TerminalChat(bootstrap.session, bootstrap.warnings).run()
