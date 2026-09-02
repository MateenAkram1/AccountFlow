import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from accountflow.core.config import ROOT_DIR, get_settings
from accountflow.models.schemas import RunRecord, RunStatus


class RunStore:
    def __init__(self, db_path: Path | None = None) -> None:
        settings = get_settings()
        if db_path:
            self._path = db_path
        elif settings.database_url.startswith("sqlite:///"):
            rel = settings.database_url.replace("sqlite:///", "")
            self._path = ROOT_DIR / rel
        else:
            self._path = ROOT_DIR / "data" / "accountflow.db"
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
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def save(self, run: RunRecord) -> RunRecord:
        run.updated_at = datetime.now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runs (id, status, data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    data=excluded.data,
                    updated_at=excluded.updated_at
                """,
                (
                    run.id,
                    run.status.value,
                    run.model_dump_json(),
                    run.created_at.isoformat(),
                    run.updated_at.isoformat(),
                ),
            )
        return run

    def get(self, run_id: str) -> RunRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT data FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return None
        return RunRecord.model_validate_json(row["data"])

    def list_runs(self, limit: int = 50) -> list[RunRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT data FROM runs ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [RunRecord.model_validate_json(r["data"]) for r in rows]


_store: RunStore | None = None


def get_run_store() -> RunStore:
    global _store
    if _store is None:
        _store = RunStore()
    return _store
