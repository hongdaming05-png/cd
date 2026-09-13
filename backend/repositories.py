"""SQLite owns progress. Compare-and-swap prevents double clicks from skipping steps."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from backend.models import Session


class ConflictError(Exception):
    pass


class SessionStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, revision INTEGER NOT NULL, payload TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, session: Session) -> None:
        with self.connection() as db:
            db.execute(
                "INSERT INTO sessions (id, revision, payload) VALUES (?, ?, ?)",
                (session.id, session.revision, session.model_dump_json()),
            )

    def get(self, session_id: str) -> Session:
        with self.connection() as db:
            row = db.execute("SELECT payload FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            raise KeyError(session_id)
        return Session.model_validate_json(row[0])

    def update(self, session: Session, expected_revision: int) -> None:
        with self.connection() as db:
            result = db.execute(
                "UPDATE sessions SET payload=?, revision=?, updated_at=CURRENT_TIMESTAMP "
                "WHERE id=? AND revision=?",
                (session.model_dump_json(), session.revision, session.id, expected_revision),
            )
            if result.rowcount != 1:
                raise ConflictError("進度已更新，請重新讀取目前步驟。")
