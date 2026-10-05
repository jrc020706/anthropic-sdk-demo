"""Chat interactivo de terminal con historial, skills y varios proveedores."""

import argparse
import os

from chat_app.infrastructure.config import (
    ConfigurationError,
    SUPPORTED_PROVIDERS,
    default_model,
)
from chat_app.infrastructure.providers import ProviderError
from chat_app.infrastructure.skill_manager import list_skills, load_skill
from chat_app.presentation.composition import create_chat_session


HELP = """Comandos:
  /help                    Muestra esta ayuda.
  /status                  Muestra la configuración de la sesión.
  /providers               Muestra los proveedores compatibles.
  /provider <nombre>       Cambia entre anthropic y openai.
  /model <nombre>          Cambia el modelo del proveedor actual.
  /skills                  Lista las skills disponibles.
  /skill <nombre|none>     Activa una skill o la desactiva.
  /new                     Borra el historial de la conversación.
  /exit                    Cierra el chat.
"""


class TerminalChat:
    def __init__(self, session) -> None:
        self.session = session

    def print_status(self) -> None:
        model = self.session.model or default_model(self.session.provider_name)
        skill = self.session.skill_name or "ninguna"
        print(
            f"Proveedor: {self.session.provider_name} | Modelo: {model} | "
            f"Skill: {skill} | Mensajes en contexto: {len(self.session.history)}"
        )

    def handle_command(self, command: str) -> bool:
        name, _, argument = command[1:].partition(" ")
        name = name.lower().strip()
        argument = argument.strip()

        if name in {"exit", "quit", "salir"}:
            return False
        if name == "help":
            print(HELP)
        elif name == "status":
            self.print_status()
        elif name == "providers":
            print("Proveedores compatibles: " + ", ".join(SUPPORTED_PROVIDERS))
        elif name == "provider":
            selected_provider = argument.lower()
            if selected_provider not in SUPPORTED_PROVIDERS:
                print("Indica un proveedor: " + ", ".join(SUPPORTED_PROVIDERS))
            else:
                self.session.provider_name = selected_provider
                self.session.model = None
                self.session.reset()
                print(f"Proveedor cambiado a {selected_provider}. Se inició una conversación nueva.")
        elif name == "model":
            if not argument:
                print("Indica el nombre del modelo.")
            else:
                self.session.model = argument
                print(f"Modelo cambiado a {argument}.")
        elif name == "skills":
            skills = list_skills()
            if skills:
                for skill in skills:
                    print(f"- {skill['name']}: {skill['description']}")
            else:
                print("No hay skills disponibles.")
        elif name == "skill":
            if argument.lower() in {"none", "ninguna", "off"}:
                self.session.skill_name = None
                self.session.reset()
                print("Skill desactivada. Se inició una conversación nueva.")
            elif load_skill(argument):
                self.session.skill_name = argument
                self.session.reset()
                print(f"Skill activada: {argument}. Se inició una conversación nueva.")
            else:
                print(f"No existe la skill '{argument}'. Usa /skills para ver las disponibles.")
        elif name == "new":
            self.session.reset()
            print("Se inició una conversación nueva.")
        else:
            print("Comando desconocido. Usa /help para ver los comandos.")
        return True

    def run(self) -> None:
        print("Chat multiproveedor. Escribe /help para ver los comandos.")
        self.print_status()
        while True:
            try:
                prompt = input("\nTú: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nHasta luego.")
                return

            if not prompt:
                continue
            if prompt.startswith("/"):
                if not self.handle_command(prompt):
                    print("Hasta luego.")
                    return
                continue

            try:
                print(f"\nAsistente: {self.session.ask(prompt)}")
            except (ConfigurationError, ProviderError, ValueError) as exc:
                print(f"\nError: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat de terminal multiproveedor.")
    parser.add_argument("--provider", choices=SUPPORTED_PROVIDERS, help="Proveedor inicial")
    parser.add_argument("--model", help="Modelo inicial")
    parser.add_argument("--skill", help="Skill inicial")
    parser.add_argument("--max-tokens", type=int, default=1000, help="Máximo de tokens de salida")
    parser.add_argument("--history-limit", type=int, default=20, help="Mensajes máximos en contexto")
    args = parser.parse_args()

    provider = args.provider or os.getenv("CHAT_PROVIDER", "anthropic").strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        parser.error("CHAT_PROVIDER debe ser uno de: " + ", ".join(SUPPORTED_PROVIDERS))
    if args.skill and not load_skill(args.skill):
        parser.error(f"No existe la skill '{args.skill}'.")
    if args.max_tokens < 1 or args.history_limit < 2:
        parser.error("--max-tokens debe ser positivo y --history-limit debe ser al menos 2.")

    TerminalChat(
        create_chat_session(
            provider_name=provider,
            model=args.model or os.getenv("CHAT_MODEL"),
            skill_name=args.skill,
            max_tokens=args.max_tokens,
            history_limit=args.history_limit,
        )
    ).run()