"""Encrypted per-user credential vault (BYOK)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from accountflow.core.config import ROOT_DIR, get_settings
from accountflow.core.security import decrypt_payload, encrypt_payload, mask_secret

ProviderName = Literal["hubspot", "jira", "llm", "stt"]
VALID_PROVIDERS: set[str] = {"hubspot", "jira", "llm", "stt"}


def _db_path(db_path: Path | None = None) -> Path:
    if db_path:
        return db_path
    settings = get_settings()
    if settings.database_url.startswith("sqlite:///"):
        rel = settings.database_url.replace("sqlite:///", "")
        return ROOT_DIR / rel
    return ROOT_DIR / "data" / "accountflow.db"


class SecretsVault:
    def __init__(self, db_path: Path | None = None) -> None:
        self._path = _db_path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_secrets (
                    user_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    payload_encrypted TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, provider)
                )
                """
            )

    def put(self, user_id: str, provider: str, payload: dict[str, Any]) -> None:
        if provider not in VALID_PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")
        encrypted = encrypt_payload(payload)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_secrets (user_id, provider, payload_encrypted, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, provider) DO UPDATE SET
                    payload_encrypted=excluded.payload_encrypted,
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
                SELECT payload_encrypted FROM user_secrets
                WHERE user_id = ? AND provider = ?
                """,
                (user_id, provider),
            ).fetchone()
        if not row:
            return None
        return decrypt_payload(row["payload_encrypted"])

    def delete(self, user_id: str, provider: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM user_secrets WHERE user_id = ? AND provider = ?",
                (user_id, provider),
            )

    def has(self, user_id: str, provider: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM user_secrets WHERE user_id = ? AND provider = ?
                """,
                (user_id, provider),
            ).fetchone()
        return row is not None

    def status(self, user_id: str) -> dict[str, Any]:
        """Return configured flags + optional last-4 hints — never full secrets."""
        result: dict[str, Any] = {}
        for provider in sorted(VALID_PROVIDERS):
            payload = self.get(user_id, provider) if self.has(user_id, provider) else None
            if not payload:
                result[provider] = {"configured": False, "hint": None}
                continue
            hint = None
            if provider == "hubspot":
                hint = mask_secret(payload.get("access_token"))
            elif provider == "jira":
                hint = mask_secret(payload.get("api_token"))
            elif provider in {"llm", "stt"}:
                hint = mask_secret(payload.get("api_key"))
            meta: dict[str, Any] = {"configured": True, "hint": hint}
            if provider == "jira":
                meta["site_url"] = payload.get("site_url")
                meta["email"] = payload.get("email")
            if provider == "llm":
                meta["provider"] = payload.get("provider")
                meta["model"] = payload.get("model")
            if provider == "stt":
                meta["provider"] = payload.get("provider")
            result[provider] = meta
        return result

    def encrypted_blob_for_tests(self, user_id: str, provider: str) -> str | None:
        """Return raw ciphertext (tests only — never expose via API)."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload_encrypted FROM user_secrets
                WHERE user_id = ? AND provider = ?
                """,
                (user_id, provider),
            ).fetchone()
        return row["payload_encrypted"] if row else None


_vault: SecretsVault | None = None


def get_secrets_vault() -> SecretsVault:
    global _vault
    if _vault is None:
        _vault = SecretsVault()
    return _vault


def clear_vault_cache() -> None:
    global _vault
    _vault = None
