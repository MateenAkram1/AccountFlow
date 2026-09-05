"""Gmail send via OAuth access token (stored after Connect) or env token."""

from __future__ import annotations

import base64
from email.mime.text import MIMEText

import httpx

from accountflow.core.config import get_settings
from accountflow.db.tokens import get_token_store
from accountflow.models.schemas import EmailDraft, ExecutionStepResult

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


class GmailClient:
    def __init__(
        self,
        access_token: str | None = None,
        *,
        user_id: str | None = None,
        allow_env_fallback: bool = True,
    ) -> None:
        self._token = access_token
        self._user_id = user_id
        self._allow_env_fallback = allow_env_fallback

    async def _resolve_access_token(self) -> str | None:
        if self._token:
            return self._token
        settings = get_settings()
        if self._allow_env_fallback and settings.gmail_access_token:
            return settings.gmail_access_token
        if not self._user_id:
            return None
        stored = get_token_store().get(self._user_id, "google")
        if not stored:
            return None
        access = stored.get("access_token")
        refresh = stored.get("refresh_token")
        if access and not refresh:
            return access
        if refresh and settings.google_oauth_configured:
            refreshed = await self._refresh(refresh)
            if refreshed:
                return refreshed
        return access

    async def _refresh(self, refresh_token: str) -> str | None:
        if not self._user_id:
            return None
        settings = get_settings()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            if resp.status_code >= 400:
                return None
            data = resp.json()
            access = data.get("access_token")
            if not access:
                return None
            stored = get_token_store().get(self._user_id, "google") or {}
            stored["access_token"] = access
            if data.get("refresh_token"):
                stored["refresh_token"] = data["refresh_token"]
            get_token_store().save(self._user_id, "google", stored)
            return access

    async def send(self, email: EmailDraft) -> ExecutionStepResult:
        settings = get_settings()
        if settings.integrations_mock:
            return ExecutionStepResult(
                step="send_email",
                success=True,
                external_id="mock-msg-001",
                message=f"Mock sent to {email.to}",
            )

        token = await self._resolve_access_token()
        if not token:
            return ExecutionStepResult(
                step="send_email",
                success=False,
                error="Gmail not connected. Open /connect and authorize Gmail.",
            )

        message = MIMEText(email.body)
        message["to"] = ", ".join(email.to)
        message["subject"] = email.subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(
                        GMAIL_SEND_URL,
                        headers=headers,
                        json={"raw": raw},
                    )
                    if resp.status_code == 401 and attempt == 0:
                        # Force refresh once
                        if self._user_id:
                            stored = get_token_store().get(self._user_id, "google") or {}
                            if stored.get("refresh_token"):
                                new_token = await self._refresh(stored["refresh_token"])
                                if new_token:
                                    headers["Authorization"] = f"Bearer {new_token}"
                                    continue
                    resp.raise_for_status()
                    data = resp.json()
                    return ExecutionStepResult(
                        step="send_email",
                        success=True,
                        external_id=data.get("id"),
                        message=f"Email sent to {', '.join(email.to)}",
                    )
                except httpx.HTTPError as e:
                    if attempt == 2:
                        detail = (
                            f"HTTP {e.response.status_code}: {e.response.text[:300]}"
                            if isinstance(e, httpx.HTTPStatusError)
                            else str(e)
                        )
                        return ExecutionStepResult(
                            step="send_email",
                            success=False,
                            error=detail,
                        )
        return ExecutionStepResult(step="send_email", success=False, error="Unknown error")

    async def ping(self) -> dict:
        token = await self._resolve_access_token()
        if not token:
            return {"ok": False, "error": "Gmail not connected"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code >= 400:
                return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            data = resp.json()
            return {"ok": True, "email": data.get("emailAddress")}
