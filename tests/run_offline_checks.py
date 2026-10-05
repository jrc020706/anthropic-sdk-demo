"""Offline acceptance checks. No API key, no network, no Supabase required.

Run it with:

    python tests/run_offline_checks.py

It verifies the parts of the acceptance criteria that do not need a live model:
the 10-message rolling window, persistent saved chats, /resume behaviour, the
RAG wiring (context injected into the system prompt), recoverable failures and
the chunking baseline (500-800 tokens with 10-20% overlap).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from chat_app.application.chat_session import ChatSession, DEFAULT_HISTORY_LIMIT
from chat_app.application.prompt_design import AdaptivePromptDesigner
from chat_app.domain.models import ProviderConfig, RetrievedChunk
from chat_app.infrastructure.rag.chunking import chunk_text, estimate_tokens
from chat_app.infrastructure.rag.loaders import UnsupportedDocumentError, load_document
from chat_app.infrastructure.session_store import SQLiteSessionStore

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"{'PASS' if condition else 'FAIL'}  {label}" + ("" if condition else f" :: {detail}"))
    if not condition:
        FAILURES.append(label)


class FakeProvider:
    """Stands in for Anthropic/OpenAI so the flow can be tested offline."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def complete(self, messages, *, system_prompt, max_tokens):
        self.calls.append({"messages": list(messages), "system": system_prompt})
        return f"answer-{len(self.calls)}"


class FakeRetriever:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def retrieve(self, query: str, top_k: int = 5):
        self.queries.append(query)
        return [
            RetrievedChunk(
                content="Run data/supabase/schema.sql to create the tables.",
                source="documents/rag-knowledge-base.md",
                score=0.87,
                chunk_index=0,
            )
        ]


def make_session(
    store=None, retriever=None, provider: FakeProvider | None = None
) -> tuple[ChatSession, FakeProvider]:
    fake = provider or FakeProvider()
    return ChatSession(
        resolve_config=lambda _p, _m: ProviderConfig(
            provider="openai", api_key="offline", base_url=None, model="gpt-4o-mini"
        ),
        provider_factory=lambda _config: fake,
        load_skill_prompt=lambda _name: "SKILL INSTRUCTIONS",
        prompt_designer=AdaptivePromptDesigner(),
        history_limit=DEFAULT_HISTORY_LIMIT,
        session_store=store,
        retriever=retriever,
    ), fake


def check_memory_window() -> None:
    session, fake = make_session()
    for index in range(1, 14):
        session.ask(f"question {index}")

    check("rolling window is capped at 10 messages", len(session.history) == 10,
          f"got {len(session.history)}")
    check("window holds the 10 most recent messages",
          session.history[0]["content"] == "question 9"
          and session.history[-1]["content"] == "answer-13",
          str(session.history[0]))
    check("window alternates user/assistant",
          [m["role"] for m in session.history] == ["user", "assistant"] * 5)
    last_call = fake.calls[-1]
    check("provider receives the window only (<= 10 messages)",
          len(last_call["messages"]) <= 10, str(len(last_call["messages"])))
    check("system instructions are sent apart from the window",
          bool(last_call["system"]) and "Knowledge base rules" in last_call["system"])


def check_saved_chats() -> None:
    tmp = tempfile.mkdtemp(prefix="offline-checks-")
    db_path = str(Path(tmp) / "chats.db")
    store = SQLiteSessionStore(db_path)

    session, _ = make_session(store)
    for index in range(1, 4):
        session.ask(f"message {index}")

    sessions = session.list_chats()
    check("session persisted to SQLite", len(sessions) == 1, str(len(sessions)))
    session_id = sessions[0].id
    check("session id is a stable short id", len(session_id) == 8, session_id)
    check("complete history stored (6 messages)", len(store.load_messages(session_id)) == 6)
    check("session title stored", bool(sessions[0].title))

    # Simulate an application restart, then resume the saved session.
    resumed, fake = make_session(SQLiteSessionStore(db_path))
    ok, message = resumed.resume(session_id)
    check("/resume accepts a known id", ok, message)
    check("/resume rebuilds the context from the last 10 messages",
          len(resumed.history) == 6, str(len(resumed.history)))

    resumed.ask("message after resume")
    stored = store.load_messages(session_id)
    check("new messages are saved back to the same session",
          len(stored) == 8 and stored[-2]["content"] == "message after resume",
          str(stored[-2:]))

    ok, message = resumed.resume("deadbeef")
    check("/resume rejects an unknown id without crashing",
          not ok and "Unknown session id" in message, message)

    other, _ = make_session(SQLiteSessionStore(db_path))
    check("/chats lists saved sessions with their id",
          any(item.id == session_id for item in other.list_chats()))


def check_rag_wiring() -> None:
    retriever = FakeRetriever()
    session, fake = make_session(retriever=retriever)
    session.ask("How do I create the Supabase tables?")

    check("retrieval happens before generation", retriever.queries ==
          ["How do I create the Supabase tables?"], str(retriever.queries))
    system_prompt = fake.calls[-1]["system"]
    check("retrieved chunks reach the system prompt",
          "documents/rag-knowledge-base.md" in system_prompt
          and "schema.sql" in system_prompt)
    check("chunk source metadata is shown to the model",
          "relevance:" in system_prompt and "chunk: 0" in system_prompt)
    check("chunks are reported for the Sources line", len(session.last_chunks) == 1)

    class BrokenRetriever:
        def retrieve(self, query, top_k=5):
            raise RuntimeError("vector store unreachable")

    broken, _ = make_session(retriever=BrokenRetriever())
    answer = broken.ask("hello")
    check("a retrieval failure never crashes the chat",
          answer.startswith("answer-") and "vector store unreachable" in
          (broken.last_retrieval_error or ""), str(broken.last_retrieval_error))

    no_rag, fake = make_session()
    no_rag.ask("hello")
    check("without context the model is told not to invent",
          "not enough information" in fake.calls[-1]["system"])


def check_chunking() -> None:
    import random

    random.seed(42)
    words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"]
    document = "\n\n".join(
        " ".join(
            " ".join(random.choice(words) for _ in range(40)) + "."
            for _ in range(6)
        )
        for _ in range(24)
    )
    chunks = chunk_text(document, target_tokens=600, overlap_ratio=0.15)
    sizes = [estimate_tokens(chunk) for chunk in chunks]
    full_sizes = sizes[:-1] if len(sizes) > 1 else sizes

    check("documents are split into several chunks", len(chunks) >= 4, str(len(chunks)))
    check("chunks stay in the 500-800 token baseline",
          all(500 <= size <= 800 for size in full_sizes), str(full_sizes))

    overlaps = []
    for index in range(1, len(chunks)):
        previous, current = chunks[index - 1], chunks[index]
        tail = previous[-int(len(previous) * 0.4) :]
        shared = 0
        for size in range(1, min(len(tail), len(current)) + 1):
            if tail[-size:] == current[:size]:
                shared = size
        overlaps.append(round(shared / max(1, len(previous)) * 100))
    check("overlap stays in the 10-20% band",
          all(9.5 <= value <= 20.5 for value in overlaps), str(overlaps))

    try:
        load_document(PROJECT_ROOT / "does-not-exist.png")
        check("unsupported document raises a readable error", False)
    except UnsupportedDocumentError as exc:
        check("unsupported document raises a readable error",
              "unsupported extension" in str(exc), str(exc))

    preview = PROJECT_ROOT / "data" / "documents"
    supported = [name for name in ("getting-started.md", "providers-and-memory.md",
                                   "rag-knowledge-base.md",
                                   "skills-and-failure-handling.md")
                 if (preview / name).exists()]
    check("at least 3 documents are available for ingestion", len(supported) >= 3,
          str(supported))


def main() -> int:
    print("Running offline acceptance checks...\n")
    check_memory_window()
    check_saved_chats()
    check_rag_wiring()
    check_chunking()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
        return 1
    print("All offline checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
