import base64
from email.mime.text import MIMEText

import httpx

from accountflow.core.config import get_settings
from accountflow.models.schemas import EmailDraft, ExecutionStepResult


class GmailClient:
    def __init__(self, access_token: str | None = None) -> None:
        self._token = access_token

    async def send(self, email: EmailDraft) -> ExecutionStepResult:
        settings = get_settings()
        if settings.integrations_mock:
            return ExecutionStepResult(
                step="send_email",
                success=True,
                external_id="mock-msg-001",
                message=f"Mock sent to {email.to}",
            )

        if not self._token:
            raise ValueError("Gmail access token required")

        message = MIMEText(email.body)
        message["to"] = ", ".join(email.to)
        message["subject"] = email.subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        headers = {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(
                        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                        headers=headers,
                        json={"raw": raw},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return ExecutionStepResult(
                        step="send_email",
                        success=True,
                        external_id=data.get("id"),
                        message="Email sent",
                    )
                except httpx.HTTPError as e:
                    if attempt == 2:
                        return ExecutionStepResult(
                            step="send_email",
                            success=False,
                            error=str(e),
                        )
        return ExecutionStepResult(step="send_email", success=False, error="Unknown error")
