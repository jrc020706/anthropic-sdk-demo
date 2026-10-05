from typing import Optional, Protocol


class PromptDesigner(Protocol):
    def build(self, skill_instructions: Optional[str] = None) -> str:
        """Compone las instrucciones de sistema para el turno actual."""


class AdaptivePromptDesigner:
    """Compone instrucciones según el modo general o la skill activa."""

    _BASE_INSTRUCTIONS = """Adapta cada respuesta a la intención y al nivel de detalle que sugiera la consulta.
- Para preguntas directas, responde de forma breve y concreta.
- Para solicitudes de aprendizaje o análisis, explica el razonamiento y organiza los pasos.
- Cuando se solicite código, entrega una solución ejecutable y señala supuestos relevantes.
- Respeta el formato y las restricciones que pida explícitamente el usuario.
- Si falta información imprescindible, pregunta antes de asumirla; no inventes datos."""

    def build(self, skill_instructions: Optional[str] = None) -> str:
        if skill_instructions:
            mode = (
                "Modo especializado: aplica las instrucciones de la skill activa y "
                "ajusta la respuesta a la tarea concreta sin perder claridad."
            )
            return f"{self._BASE_INSTRUCTIONS}\n\n{mode}\n\n{skill_instructions}"

        mode = (
            "Modo general: identifica primero el tipo de ayuda que requiere la consulta "
            "y elige una respuesta proporcional, sin imponer una especialidad no solicitada."
        )
        return f"{self._BASE_INSTRUCTIONS}\n\n{mode}"