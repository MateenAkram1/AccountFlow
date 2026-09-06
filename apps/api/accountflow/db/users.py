"""Users and invite allowlist (SQLite / Turso)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from accountflow.core.config import get_settings
from accountflow.db.connection import connect_db

AuthProvider = Literal["password", "google", "both"]


@dataclass
class User:
    id: str
    email: str
    password_hash: str | None
    name: str | None
    auth_provider: AuthProvider
    created_at: str


class UserStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path
        self._init_db()

    def _connect(self):
        return connect_db(db_path=self._db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT,
                    name TEXT,
                    auth_provider TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS allowlist (
                    email TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    created_by TEXT
                )
                """
            )

    def seed_allowlist_from_env(self) -> int:
        settings = get_settings()
        added = 0
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            for email in settings.allowlist_emails:
                cur = conn.execute(
                    """
                    INSERT INTO allowlist (email, created_at, created_by)
                    VALUES (?, ?, ?)
                    ON CONFLICT(email) DO NOTHING
                    """,
                    (email, now, "env"),
                )
                added += cur.rowcount
        return added

    def is_allowlisted(self, email: str) -> bool:
        email_n = email.strip().lower()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM allowlist WHERE email = ?", (email_n,)
            ).fetchone()
        return row is not None

    def add_allowlist(self, email: str, created_by: str = "admin") -> None:
        email_n = email.strip().lower()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO allowlist (email, created_at, created_by)
                VALUES (?, ?, ?)
                ON CONFLICT(email) DO NOTHING
                """,
                (email_n, datetime.now(timezone.utc).isoformat(), created_by),
            )

    def _row_to_user(self, row: Any) -> User:
        return User(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            name=row["name"],
            auth_provider=row["auth_provider"],  # type: ignore[arg-type]
            created_at=row["created_at"],
        )

    def get_by_id(self, user_id: str) -> User | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self._row_to_user(row) if row else None

    def get_by_email(self, email: str) -> User | None:
        email_n = email.strip().lower()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email_n,)
            ).fetchone()
        return self._row_to_user(row) if row else None

    def ensure_session_user(self, *, user_id: str, email: str, name: str | None = None) -> User:
        """Restore a user row from a valid JWT (needed when SQLite is ephemeral)."""
        existing = self.get_by_id(user_id)
        if existing:
            return existing
        email_n = email.strip().lower()
        by_email = self.get_by_email(email_n)
        if by_email:
            return by_email
        user = User(
            id=user_id,
            email=email_n,
            password_hash=None,
            name=name,
            auth_provider="password",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (id, email, password_hash, name, auth_provider, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user.id,
                    user.email,
                    user.password_hash,
                    user.name,
                    user.auth_provider,
                    user.created_at,
                ),
            )
        return user

    def create_password_user(
        self, *, email: str, password_hash: str, name: str | None = None
    ) -> User:
        email_n = email.strip().lower()
        user = User(
            id=str(uuid4()),
            email=email_n,
            password_hash=password_hash,
            name=name,
            auth_provider="password",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (id, email, password_hash, name, auth_provider, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user.id,
                    user.email,
                    user.password_hash,
                    user.name,
                    user.auth_provider,
                    user.created_at,
                ),
            )
        return user

    def upsert_google_user(self, *, email: str, name: str | None = None) -> User:
        existing = self.get_by_email(email)
        if existing:
            provider: AuthProvider = (
                "both" if existing.password_hash else "google"
            )
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE users SET name = COALESCE(?, name), auth_provider = ?
                    WHERE id = ?
                    """,
                    (name, provider, existing.id),
                )
            updated = self.get_by_id(existing.id)
            assert updated is not None
            return updated

        user = User(
            id=str(uuid4()),
            email=email.strip().lower(),
            password_hash=None,
            name=name,
            auth_provider="google",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (id, email, password_hash, name, auth_provider, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user.id,
                    user.email,
                    None,
                    user.name,
                    user.auth_provider,
                    user.created_at,
                ),
            )
        return user

    def set_password(self, user_id: str, password_hash: str) -> None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT auth_provider FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not row:
                return
            provider = "both" if row["auth_provider"] == "google" else "password"
            conn.execute(
                """
                UPDATE users SET password_hash = ?, auth_provider = ? WHERE id = ?
                """,
                (password_hash, provider, user_id),
            )


_user_store: UserStore | None = None


def get_user_store() -> UserStore:
    global _user_store
    if _user_store is None:
        _user_store = UserStore()
    return _user_store


def clear_user_store_cache() -> None:
    global _user_store
    _user_store = None
