import httpx

from accountflow.core.config import get_settings
from accountflow.models.schemas import AccountDossier, Contact, CRMUpdate, ExecutionStepResult


class HubSpotClient:
    def __init__(self, access_token: str | None = None) -> None:
        self._token = access_token
        self._base = "https://api.hubapi.com"

    async def get_deal(self, deal_id: str) -> AccountDossier:
        settings = get_settings()
        if settings.integrations_mock:
            return _mock_account(deal_id)

        if not self._token:
            raise ValueError("HubSpot access token required")

        headers = {"Authorization": f"Bearer {self._token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            deal_resp = await client.get(
                f"{self._base}/crm/v3/objects/deals/{deal_id}",
                headers=headers,
                params={"properties": "dealname,dealstage,amount,closedate"},
            )
            deal_resp.raise_for_status()
            deal = deal_resp.json()
            props = deal.get("properties", {})

            notes_resp = await client.get(
                f"{self._base}/crm/v3/objects/deals/{deal_id}/associations/notes",
                headers=headers,
            )
            notes = []
            if notes_resp.status_code == 200:
                for assoc in notes_resp.json().get("results", [])[:5]:
                    notes.append(f"Note id: {assoc.get('id')}")

        return AccountDossier(
            deal_id=deal_id,
            company=props.get("dealname", "Unknown"),
            stage=props.get("dealstage", "unknown"),
            amount=float(props["amount"]) if props.get("amount") else None,
            close_date=props.get("closedate"),
            contacts=[],
            notes=notes,
        )

    async def update_deal(self, deal_id: str, updates: list[CRMUpdate]) -> ExecutionStepResult:
        settings = get_settings()
        if settings.integrations_mock:
            return ExecutionStepResult(
                step="update_crm",
                success=True,
                external_id=f"mock-deal-{deal_id}",
                message=f"Mock updated {len(updates)} fields",
            )

        if not self._token:
            raise ValueError("HubSpot access token required")

        properties = {u.field: u.value for u in updates}
        headers = {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(3):
                try:
                    resp = await client.patch(
                        f"{self._base}/crm/v3/objects/deals/{deal_id}",
                        headers=headers,
                        json={"properties": properties},
                    )
                    resp.raise_for_status()
                    return ExecutionStepResult(
                        step="update_crm",
                        success=True,
                        external_id=deal_id,
                        message="Deal updated",
                    )
                except httpx.HTTPError as e:
                    if attempt == 2:
                        return ExecutionStepResult(
                            step="update_crm",
                            success=False,
                            error=str(e),
                        )
        return ExecutionStepResult(step="update_crm", success=False, error="Unknown error")


def _mock_account(deal_id: str) -> AccountDossier:
    return AccountDossier(
        deal_id=deal_id,
        company="Acme Corp",
        stage="discovery",
        amount=40000.0,
        close_date="2026-03-31",
        contacts=[Contact(name="Sarah Chen", role="CTO", email="sarah@acme.example")],
        notes=["Feb 10: Discussed API integration timeline"],
    )
