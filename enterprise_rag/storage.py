from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import SETTINGS


class ChatStore:
    def __init__(self, path: Path | None = None):
        self.path = path or SETTINGS.database_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, username TEXT NOT NULL,
                    role TEXT NOT NULL, content TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY, message_id INTEGER, session_id TEXT NOT NULL,
                    username TEXT NOT NULL, rating INTEGER NOT NULL CHECK(rating IN (-1, 1)),
                    comment TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
                    UNIQUE(session_id, message_id, username)
                );
            """)

    def add_message(self, session_id: str, username: str, role: str, content: str, metadata=None) -> int:
        with self.connect() as db:
            cursor = db.execute(
                "INSERT INTO messages(session_id, username, role, content, metadata, created_at) VALUES(?,?,?,?,?,?)",
                (session_id, username, role, content, json.dumps(metadata or {}), datetime.now(timezone.utc).isoformat()),
            )
            return int(cursor.lastrowid)

    def history(self, session_id: str, username: str, limit: int = 100) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, role, content, metadata FROM messages WHERE session_id=? AND username=? ORDER BY id DESC LIMIT ?",
                (session_id, username, limit),
            ).fetchall()
        return [dict(id=r["id"], role=r["role"], content=r["content"], metadata=json.loads(r["metadata"])) for r in reversed(rows)]

    def add_feedback(self, message_id: int, session_id: str, username: str, rating: int, comment: str = "") -> None:
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO feedback(message_id, session_id, username, rating, comment, created_at) VALUES(?,?,?,?,?,?)",
                (message_id, session_id, username, rating, comment[:1000], datetime.now(timezone.utc).isoformat()),
            )
