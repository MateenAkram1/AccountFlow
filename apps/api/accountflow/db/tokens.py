"""Per-user OAuth / preference token store with Fernet encryption at rest."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from accountflow.core.config import data_dir
from accountflow.core.security import decrypt_payload, encrypt_payload
from accountflow.db.connection import connect_db, uses_turso


class TokenStore:
    def __init__(self, db_path: Path | None = None) -> None:
        # Local path only when not using Turso (keeps oauth tables in the same remote DB).
        self._db_path = db_path if db_path is not None else (None if uses_turso() else data_dir() / "tokens.db")
        if self._db_path is not None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        return connect_db(db_path=self._db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_tokens (
                    user_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    data_encrypted TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, provider)
                )
                """
            )
            # Migrate legacy global table if present (plaintext provider PK)
            cols = {
                r["name"]
                for r in conn.execute("PRAGMA table_info(oauth_tokens)").fetchall()
            }
            if "data" in cols and "data_encrypted" not in cols:
                # Very old schema — leave alone; new writes use new table name
                pass
            # Drop orphan legacy single-column PK table by renaming if needed
            legacy = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='oauth_tokens_legacy'"
            ).fetchone()
            if not legacy:
                # If old schema (provider PK, data plaintext) exists without user_id
                info = conn.execute("PRAGMA table_info(oauth_tokens)").fetchall()
                col_names = {r["name"] for r in info}
                if col_names == {"provider", "data", "updated_at"}:
                    conn.execute("ALTER TABLE oauth_tokens RENAME TO oauth_tokens_legacy")
                    conn.execute(
                        """
                        CREATE TABLE oauth_tokens (
                            user_id TEXT NOT NULL,
                            provider TEXT NOT NULL,
                            data_encrypted TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            PRIMARY KEY (user_id, provider)
                        )
                        """
                    )

    def save(self, user_id: str, provider: str, data: dict[str, Any]) -> None:
        encrypted = encrypt_payload(data)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO oauth_tokens (user_id, provider, data_encrypted, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, provider) DO UPDATE SET
                    data_encrypted=excluded.data_encrypted,
                    updated_at=excluded.updated_at
                """,
                (
                    user_id,
                    provider,
                    encrypted,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def get(self, user_id: str, provider: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT data_encrypted FROM oauth_tokens
                WHERE user_id = ? AND provider = ?
                """,
                (user_id, provider),
            ).fetchone()
        if not row:
            return None
        return decrypt_payload(row["data_encrypted"])

    def delete(self, user_id: str, provider: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM oauth_tokens WHERE user_id = ? AND provider = ?",
                (user_id, provider),
            )

    def has(self, user_id: str, provider: str) -> bool:
        return self.get(user_id, provider) is not None

    def encrypted_blob_for_tests(self, user_id: str, provider: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT data_encrypted FROM oauth_tokens
                WHERE user_id = ? AND provider = ?
                """,
                (user_id, provider),
            ).fetchone()
        return row["data_encrypted"] if row else None


_store: TokenStore | None = None


def get_token_store() -> TokenStore:
    global _store
    if _store is None:
        _store = TokenStore()
    return _store


def clear_token_store_cache() -> None:
    global _store
    _store = None
