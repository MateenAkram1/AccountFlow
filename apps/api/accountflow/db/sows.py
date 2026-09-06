"""Per-user saved Statements of Work (reusable across runs)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from accountflow.db.connection import connect_db


@dataclass
class SavedSow:
    id: str
    user_id: str
    name: str
    content: str
    source_filename: str | None
    created_at: str
    updated_at: str


class SowStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path
        self._init_db()

    def _connect(self):
        return connect_db(db_path=self._db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS saved_sows (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_filename TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sows_user ON saved_sows(user_id, updated_at DESC)"
            )

    def _row(self, row: Any) -> SavedSow:
        return SavedSow(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            content=row["content"],
            source_filename=row["source_filename"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_for_user(self, user_id: str) -> list[SavedSow]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM saved_sows
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [self._row(r) for r in rows]

    def get_for_user(self, sow_id: str, user_id: str) -> SavedSow | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM saved_sows WHERE id = ? AND user_id = ?",
                (sow_id, user_id),
            ).fetchone()
        return self._row(row) if row else None

    def create(
        self,
        *,
        user_id: str,
        name: str,
        content: str,
        source_filename: str | None = None,
    ) -> SavedSow:
        now = datetime.now(timezone.utc).isoformat()
        sow = SavedSow(
            id=str(uuid4()),
            user_id=user_id,
            name=name.strip() or "Untitled SOW",
            content=content,
            source_filename=source_filename,
            created_at=now,
            updated_at=now,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO saved_sows
                (id, user_id, name, content, source_filename, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sow.id,
                    sow.user_id,
                    sow.name,
                    sow.content,
                    sow.source_filename,
                    sow.created_at,
                    sow.updated_at,
                ),
            )
        return sow

    def update(
        self,
        sow_id: str,
        user_id: str,
        *,
        name: str | None = None,
        content: str | None = None,
    ) -> SavedSow | None:
        existing = self.get_for_user(sow_id, user_id)
        if not existing:
            return None
        new_name = name.strip() if name is not None else existing.name
        new_content = content if content is not None else existing.content
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE saved_sows
                SET name = ?, content = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (new_name, new_content, now, sow_id, user_id),
            )
        return self.get_for_user(sow_id, user_id)

    def delete(self, sow_id: str, user_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM saved_sows WHERE id = ? AND user_id = ?",
                (sow_id, user_id),
            )
            return cur.rowcount > 0


_store: SowStore | None = None


def get_sow_store() -> SowStore:
    global _store
    if _store is None:
        _store = SowStore()
    return _store


def clear_sow_store_cache() -> None:
    global _store
    _store = None
