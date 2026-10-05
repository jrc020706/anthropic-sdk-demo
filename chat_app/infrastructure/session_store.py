from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from chat_app.domain.models import ChatMessage, SessionSummary

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "chats.db"


class SessionStoreError(RuntimeError):
    """Recoverable error while reading or writing saved chats."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_db_path(db_path: Optional[str] = None) -> Path:
    """Resolves the SQLite file, honouring ``CHAT_DB_PATH`` when set."""
    raw = (db_path or os.getenv("CHAT_DB_PATH", "")).strip()
    path = Path(raw).expanduser() if raw else DEFAULT_DB_PATH
    return path if path.is_absolute() else Path.cwd() / path


class SQLiteSessionStore:
    """Local SQLite store so saved chats survive an application restart."""

    def __init__(self, db_path: Optional[str] = None, *, create_dirs: bool = True) -> None:
        self.path = resolve_db_path(db_path)
        if create_dirs:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._connection = sqlite3.connect(str(self.path), check_same_thread=False)
        except sqlite3.Error as exc:
            raise SessionStoreError(
                f"Cannot open the chat database at {self.path}: {exc}"
            ) from exc
        self._connection.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        try:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id         TEXT PRIMARY KEY,
                    title      TEXT NOT NULL DEFAULT '',
                    provider   TEXT NOT NULL,
                    model      TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL
                                   REFERENCES sessions(id) ON DELETE CASCADE,
                    position   INTEGER NOT NULL,
                    role       TEXT NOT NULL,
                    content    TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id, position);
                """
            )
            self._connection.commit()
        except sqlite3.Error as exc:
            raise SessionStoreError(f"Cannot initialise the chat database: {exc}") from exc

    # -- sessions ---------------------------------------------------------
    def create_session(self, provider: str, model: str = "") -> str:
        session_id = uuid.uuid4().hex[:8]
        now = _utc_now()
        while self.exists(session_id):
            session_id = uuid.uuid4().hex[:8]
        try:
            self._connection.execute(
                "INSERT INTO sessions (id, title, provider, model, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, "", provider, model, now, now),
            )
            self._connection.commit()
        except sqlite3.Error as exc:
            raise SessionStoreError(f"Cannot create a chat session: {exc}") from exc
        return session_id

    def exists(self, session_id: str) -> bool:
        try:
            row = self._connection.execute(
                "SELECT 1 FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        except sqlite3.Error as exc:
            raise SessionStoreError(f"Cannot read saved chats: {exc}") from exc
        return row is not None

    def set_title(self, session_id: str, title: str) -> None:
        cleaned = " ".join(title.split())[:80]
        if not cleaned:
            return
        try:
            self._connection.execute(
                "UPDATE sessions SET title = ? WHERE id = ?", (cleaned, session_id)
            )
            self._connection.commit()
        except sqlite3.Error as exc:
            raise SessionStoreError(f"Cannot update the session title: {exc}") from exc

    def list_sessions(self) -> list[SessionSummary]:
        try:
            rows = self._connection.execute(
                """
                SELECT s.id, s.provider, s.model, s.title, s.created_at, s.updated_at,
                       COUNT(m.id) AS message_count
                  FROM sessions s
                  LEFT JOIN messages m ON m.session_id = s.id
                 GROUP BY s.id
                 ORDER BY s.updated_at DESC
                """
            ).fetchall()
        except sqlite3.Error as exc:
            raise SessionStoreError(f"Cannot list saved chats: {exc}") from exc
        return [
            SessionSummary(
                id=row["id"],
                provider=row["provider"],
                model=row["model"],
                title=row["title"],
                message_count=row["message_count"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    # -- messages ---------------------------------------------------------
    def append(self, session_id: str, role: str, content: str) -> None:
        if not self.exists(session_id):
            raise SessionStoreError(f"Unknown session id '{session_id}'.")
        try:
            row = self._connection.execute(
                "SELECT COALESCE(MAX(position), 0) AS last FROM messages"
                " WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            position = int(row["last"]) + 1
            self._connection.execute(
                "INSERT INTO messages (session_id, position, role, content, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (session_id, position, role, content, _utc_now()),
            )
            self._connection.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (_utc_now(), session_id),
            )
            self._connection.commit()
        except sqlite3.Error as exc:
            raise SessionStoreError(f"Cannot save the message to {session_id}: {exc}") from exc

    def load_messages(self, session_id: str) -> list[ChatMessage]:
        try:
            rows = self._connection.execute(
                "SELECT role, content FROM messages WHERE session_id = ?"
                " ORDER BY position",
                (session_id,),
            ).fetchall()
        except sqlite3.Error as exc:
            raise SessionStoreError(f"Cannot load session {session_id}: {exc}") from exc
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    def close(self) -> None:
        try:
            self._connection.close()
        except sqlite3.Error:
            pass


def create_session_store(db_path: Optional[str] = None) -> SQLiteSessionStore:
    """Factory used by the presentation layer."""
    return SQLiteSessionStore(db_path)
