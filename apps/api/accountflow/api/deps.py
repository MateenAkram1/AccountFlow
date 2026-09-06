"""FastAPI auth dependencies: current user + CSRF for cookie sessions."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Cookie, Header, HTTPException, Request, status

from accountflow.core.security import (
    CSRF_HEADER,
    CSRF_VALUE,
    SESSION_COOKIE,
    decode_access_token,
)
from accountflow.db.users import User, get_user_store


@dataclass
class CurrentUser:
    id: str
    email: str
    name: str | None


def user_to_current(user: User) -> CurrentUser:
    return CurrentUser(id=user.id, email=user.email, name=user.name)


async def get_current_user(
    request: Request,
    accountflow_session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> CurrentUser:
    token = accountflow_session
    if not token:
        auth = request.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = decode_access_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        ) from exc

    user_id = payload.get("sub")
    email = (payload.get("email") or "").strip().lower()
    if not user_id or not email:
        raise HTTPException(status_code=401, detail="Invalid session")

    store = get_user_store()
    user = store.get_by_id(str(user_id))
    if not user:
        # Vercel/serverless SQLite can lose rows between cold starts while the JWT remains valid.
        user = store.ensure_session_user(user_id=str(user_id), email=email)
    return user_to_current(user)


async def require_csrf(
    request: Request,
    x_requested_with: str | None = Header(default=None, alias=CSRF_HEADER),
) -> None:
    """Require custom header on cookie-authenticated mutating requests."""
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    if x_requested_with != CSRF_VALUE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing {CSRF_HEADER} header",
        )
