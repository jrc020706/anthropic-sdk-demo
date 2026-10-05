from __future__ import annotations

from typing import Optional, Protocol, Sequence

from chat_app.domain.models import RetrievedChunk


class PromptDesigner(Protocol):
    def build(
        self,
        skill_instructions: Optional[str] = None,
        context_chunks: Optional[Sequence[RetrievedChunk]] = None,
    ) -> str:
        """Composes the system instructions for the current turn."""


class AdaptivePromptDesigner:
    """Composes instructions for general mode, skill mode and RAG context."""

    _BASE_INSTRUCTIONS = """Tune every answer to the intent and to the level of detail the question requires.
- For direct questions, answer briefly and concretely.
- For learning or analysis requests, explain the reasoning and organise the steps.
- When code is requested, deliver an executable solution and point out relevant assumptions.
- Respect any format or constraint the user explicitly asks for.
- If essential information is missing, ask before assuming it; never invent data."""

    _CONTEXT_RULES = """Knowledge base rules:
- Ground the answer in the retrieved context above whenever the question is about the project documentation.
- Cite the file name from the `source` field when you use a chunk.
- If the context does not support an answer, say there is not enough information in the knowledge base instead of inventing content."""

    _NO_CONTEXT_RULES = """Knowledge base rules:
- No relevant chunk was retrieved for this turn.
- If the question requires knowledge from the local knowledge base, reply that there is not enough information in the knowledge base instead of guessing."""

    def build(
        self,
        skill_instructions: Optional[str] = None,
        context_chunks: Optional[Sequence[RetrievedChunk]] = None,
    ) -> str:
        sections = [self._BASE_INSTRUCTIONS]

        if skill_instructions:
            sections.append(
                "Specialised mode: apply the active skill instructions and adapt the "
                "answer to the concrete task without losing clarity."
            )
            sections.append(skill_instructions)
        else:
            sections.append(
                "General mode: first identify the kind of help the question needs and "
                "choose a proportional answer, without imposing an unsolicited speciality."
            )

        if context_chunks:
            blocks = "\n\n".join(chunk.as_context_block() for chunk in context_chunks)
            sections.append(f"Retrieved knowledge-base chunks:\n\n{blocks}")
            sections.append(self._CONTEXT_RULES)
        else:
            sections.append(self._NO_CONTEXT_RULES)

        return "\n\n".join(sections)
