"""SQLite + Turso (libSQL) connection factory."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Sequence

from accountflow.core.config import get_settings, resolve_sqlite_file


class DictRow(dict):
    """Dict that also supports sqlite3.Row-style key access."""

    def __getitem__(self, key: Any) -> Any:  # noqa: ANN401
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class _CursorCompat:
    def __init__(self, cursor: Any) -> None:
        self._cursor = cursor

    def _wrap_row(self, row: Any) -> Any:
        if row is None:
            return None
        if isinstance(row, dict) or hasattr(row, "keys"):
            return row
        description = getattr(self._cursor, "description", None)
        if not description:
            return row
        cols = [col[0] for col in description]
        return DictRow(zip(cols, row, strict=False))

    def fetchone(self) -> Any:
        return self._wrap_row(self._cursor.fetchone())

    def fetchall(self) -> list[Any]:
        return [self._wrap_row(r) for r in self._cursor.fetchall()]

    def fetchmany(self, size: int | None = None) -> list[Any]:
        rows = self._cursor.fetchmany(size) if size is not None else self._cursor.fetchmany()
        return [self._wrap_row(r) for r in rows]

    def __iter__(self) -> Iterable[Any]:
        for row in self._cursor:
            yield self._wrap_row(row)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cursor, name)


class _ConnCompat:
    """Wrap libsql/sqlite connections so rows support row['col'] access."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def execute(self, sql: str, parameters: Sequence[Any] | None = None) -> _CursorCompat:
        if parameters is None:
            cur = self._conn.execute(sql)
        else:
            cur = self._conn.execute(sql, parameters)
        return _CursorCompat(cur)

    def executemany(self, sql: str, parameters: Iterable[Sequence[Any]]) -> _CursorCompat:
        return _CursorCompat(self._conn.executemany(sql, parameters))

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> _ConnCompat:
        entered = self._conn.__enter__()
        if entered is self._conn:
            return self
        return _ConnCompat(entered)

    def __exit__(self, exc_type, exc, tb) -> bool | None:  # noqa: ANN001
        return self._conn.__exit__(exc_type, exc, tb)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)


def uses_turso() -> bool:
    settings = get_settings()
    if settings.app_env.lower() in {"test"}:
        return False
    return bool(settings.turso_database_url.strip() and settings.turso_auth_token.strip())


def connect_db(
    *,
    db_path: Path | None = None,
    check_same_thread: bool = True,
) -> _ConnCompat:
    """
    Open a DB connection.

    - Explicit ``db_path`` → local sqlite (tests).
    - Else if TURSO_* set → remote Turso/libSQL.
    - Else → local sqlite from DATABASE_URL.
    """
    if db_path is not None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=check_same_thread)
        conn.row_factory = sqlite3.Row
        return _ConnCompat(conn)

    settings = get_settings()
    if uses_turso():
        import libsql

        conn = libsql.connect(
            database=settings.turso_database_url.strip(),
            auth_token=settings.turso_auth_token.strip(),
        )
        return _ConnCompat(conn)

    path = resolve_sqlite_file(settings.database_url)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=check_same_thread)
    conn.row_factory = sqlite3.Row
    return _ConnCompat(conn)
