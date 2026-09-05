"""Password hashing, JWT sessions, Fernet vault, and log redaction."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from accountflow.core.config import get_settings

SESSION_COOKIE = "accountflow_session"
CSRF_HEADER = "X-Requested-With"
CSRF_VALUE = "XMLHttpRequest"

_SENSITIVE_KEYS = re.compile(
    r"(authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|password|"
    r"client_secret|secret|bearer|jira_api_token|hubspot)",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"(Bearer\s+)([A-Za-z0-9._\-+/=]{8,})", re.IGNORECASE)
_LONG_SECRET_RE = re.compile(r"(['\"]?)([A-Za-z0-9_\-]{24,})\1")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(*, user_id: str, email: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expiry_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def get_fernet() -> Fernet:
    settings = get_settings()
    key = (settings.credentials_fernet_key or "").strip()
    if not key:
        raise RuntimeError("CREDENTIALS_FERNET_KEY is required")
    return Fernet(key.encode("utf-8") if isinstance(key, str) else key)


def encrypt_payload(data: dict[str, Any]) -> str:
    import json

    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return get_fernet().encrypt(raw).decode("utf-8")


def decrypt_payload(token: str) -> dict[str, Any]:
    import json

    try:
        raw = get_fernet().decrypt(token.encode("utf-8"))
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt credential payload") from exc
    return json.loads(raw.decode("utf-8"))


def mask_secret(value: str | None, visible: int = 4) -> str | None:
    if not value:
        return None
    if len(value) <= visible:
        return "…"
    return f"…{value[-visible:]}"


def redact_text(text: str) -> str:
    if not text:
        return text
    redacted = _BEARER_RE.sub(r"\1[REDACTED]", text)
    return redacted


def redact_mapping(data: Any) -> Any:
    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for k, v in data.items():
            if _SENSITIVE_KEYS.search(str(k)):
                out[k] = "[REDACTED]"
            else:
                out[k] = redact_mapping(v)
        return out
    if isinstance(data, list):
        return [redact_mapping(x) for x in data]
    if isinstance(data, str):
        return redact_text(data)
    return data


def cookie_secure() -> bool:
    return get_settings().app_env.lower() not in {"development", "test", "dev"}
