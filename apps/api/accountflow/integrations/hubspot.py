import httpx

from accountflow.core.config import get_settings
from accountflow.models.schemas import AccountDossier, Contact, CRMUpdate, ExecutionStepResult


class HubSpotClient:
    def __init__(
        self,
        access_token: str | None = None,
        *,
        allow_env_fallback: bool = True,
    ) -> None:
        settings = get_settings()
        token = (access_token or "").strip()
        if not token and allow_env_fallback:
            token = (settings.hubspot_access_token or "").strip()
        self._token = token
        self._base = "https://api.hubapi.com"

    async def get_deal(self, deal_id: str) -> AccountDossier:
        settings = get_settings()
        if settings.integrations_mock:
            return _mock_account(deal_id)

        if not self._token:
            raise ValueError(
                "HubSpot access token required. Configure it in Settings → Credentials."
            )

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

            notes: list[str] = []
            notes_resp = await client.get(
                f"{self._base}/crm/v3/objects/deals/{deal_id}/associations/notes",
                headers=headers,
            )
            if notes_resp.status_code == 200:
                for assoc in notes_resp.json().get("results", [])[:5]:
                    notes.append(f"Note id: {assoc.get('id')}")

            contacts: list[Contact] = []
            assoc_resp = await client.get(
                f"{self._base}/crm/v3/objects/deals/{deal_id}/associations/contacts",
                headers=headers,
            )
            if assoc_resp.status_code == 200:
                for assoc in assoc_resp.json().get("results", [])[:3]:
                    cid = assoc.get("id")
                    if not cid:
                        continue
                    c_resp = await client.get(
                        f"{self._base}/crm/v3/objects/contacts/{cid}",
                        headers=headers,
                        params={"properties": "firstname,lastname,email,jobtitle"},
                    )
                    if c_resp.status_code == 200:
                        cp = c_resp.json().get("properties", {})
                        name = " ".join(
                            p for p in [cp.get("firstname"), cp.get("lastname")] if p
                        ).strip() or "Contact"
                        contacts.append(
                            Contact(
                                name=name,
                                role=cp.get("jobtitle"),
                                email=cp.get("email"),
                            )
                        )

        return AccountDossier(
            deal_id=deal_id,
            company=props.get("dealname", "Unknown"),
            stage=props.get("dealstage", "unknown"),
            amount=float(props["amount"]) if props.get("amount") else None,
            close_date=props.get("closedate"),
            contacts=contacts,
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
            return ExecutionStepResult(
                step="update_crm",
                success=False,
                error="HubSpot token missing. Configure it in Settings → Credentials.",
            )

        # Skip demo/sample deal IDs that aren't real HubSpot objects
        if deal_id.startswith("demo-") or deal_id == "eval":
            return ExecutionStepResult(
                step="update_crm",
                success=False,
                error=(
                    f"Deal id '{deal_id}' is a sample id. Use a real HubSpot deal id "
                    "or leave CRM section rejected for sample runs."
                ),
            )

        properties = _normalize_hubspot_properties(updates)
        if not properties:
            return ExecutionStepResult(
                step="update_crm",
                success=False,
                error="No valid HubSpot properties to update after stage/field normalization",
            )

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
                        message=f"Deal updated: {', '.join(f'{k}={v}' for k, v in properties.items())}",
                    )
                except httpx.HTTPError as e:
                    if attempt == 2:
                        detail = _http_detail(e)
                        return ExecutionStepResult(
                            step="update_crm",
                            success=False,
                            error=detail,
                        )
        return ExecutionStepResult(step="update_crm", success=False, error="Unknown error")

    async def list_deals(self, limit: int = 20) -> list[dict]:
        if not self._token:
            raise ValueError("HubSpot token missing")
        headers = {"Authorization": f"Bearer {self._token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self._base}/crm/v3/objects/deals",
                headers=headers,
                params={
                    "limit": limit,
                    "properties": "dealname,dealstage,amount,closedate",
                },
            )
            resp.raise_for_status()
            deals = []
            for row in resp.json().get("results", []):
                props = row.get("properties", {})
                deals.append(
                    {
                        "id": row.get("id"),
                        "name": props.get("dealname") or f"Deal {row.get('id')}",
                        "stage": props.get("dealstage"),
                        "amount": props.get("amount"),
                    }
                )
            return deals

    async def ensure_demo_deal(self) -> dict:
        """Create a sample deal if the portal has none — enables live CRM execute."""
        existing = await self.list_deals(limit=5)
        if existing:
            return existing[0]
        if not self._token:
            raise ValueError("HubSpot token missing")
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        payload = {
            "properties": {
                "dealname": "AccountFlow OS — Acme Corp",
                "dealstage": "appointmentscheduled",
                "amount": "40000",
                "pipeline": "default",
            }
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base}/crm/v3/objects/deals",
                headers=headers,
                json=payload,
            )
            if resp.status_code >= 400:
                # Retry without pipeline if portal uses different pipelines
                payload["properties"].pop("pipeline", None)
                resp = await client.post(
                    f"{self._base}/crm/v3/objects/deals",
                    headers=headers,
                    json=payload,
                )
            resp.raise_for_status()
            data = resp.json()
            props = data.get("properties", {})
            return {
                "id": data.get("id"),
                "name": props.get("dealname") or "AccountFlow OS — Acme Corp",
                "stage": props.get("dealstage"),
                "amount": props.get("amount"),
                "created": True,
            }

    async def ping(self) -> dict:
        """Verify token works."""
        if not self._token:
            return {"ok": False, "error": "No HubSpot token configured"}
        try:
            deals = await self.list_deals(limit=1)
            return {
                "ok": True,
                "deals_sample": len(deals),
                "first_deal_id": deals[0]["id"] if deals else None,
            }
        except httpx.HTTPError as e:
            detail = _http_detail(e) if isinstance(e, httpx.HTTPError) else str(e)
            return {"ok": False, "error": detail}


def _http_detail(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}: {exc.response.text[:300]}"
    return str(exc)


# Default HubSpot Sales pipeline stage IDs (free/default pipeline)
_VALID_DEAL_STAGES = {
    "appointmentscheduled",
    "qualifiedtobuy",
    "presentationscheduled",
    "decisionmakerboughtin",
    "contractsent",
    "closedwon",
    "closedlost",
}

_STAGE_ALIASES = {
    "discovery": "appointmentscheduled",
    "appointment": "appointmentscheduled",
    "appointmentscheduled": "appointmentscheduled",
    "qualified": "qualifiedtobuy",
    "qualifiedtobuy": "qualifiedtobuy",
    "proposal": "presentationscheduled",
    "presentation": "presentationscheduled",
    "presentationscheduled": "presentationscheduled",
    "demo": "presentationscheduled",
    "negotiation": "decisionmakerboughtin",
    "decisionmakerboughtin": "decisionmakerboughtin",
    "contract": "contractsent",
    "contractsent": "contractsent",
    "won": "closedwon",
    "closedwon": "closedwon",
    "lost": "closedlost",
    "closedlost": "closedlost",
    # Common LLM inventions
    "proposalstage": "presentationscheduled",
    "proposaldraft": "presentationscheduled",
    "closing": "contractsent",
}


def _normalize_hubspot_properties(updates: list[CRMUpdate]) -> dict[str, str]:
    """Map draft CRM fields onto HubSpot-safe deal properties."""
    props: dict[str, str] = {}
    for update in updates:
        field = (update.field or "").strip().lower().replace(" ", "").replace("-", "")
        value = (update.value or "").strip()
        if not field or not value:
            continue

        if field in {"dealstage", "stage", "deal_stage", "pipeline_stage", "status"}:
            stage_key = value.lower().replace(" ", "").replace("_", "").replace("-", "")
            mapped = _STAGE_ALIASES.get(stage_key) or _STAGE_ALIASES.get(value.lower())
            if not mapped and value.lower() in _VALID_DEAL_STAGES:
                mapped = value.lower()
            if not mapped:
                # Best-effort: treat proposal-like words as presentation stage
                if "propos" in stage_key or "present" in stage_key:
                    mapped = "presentationscheduled"
                elif "close" in stage_key and "won" in stage_key:
                    mapped = "closedwon"
                else:
                    mapped = "qualifiedtobuy"
            props["dealstage"] = mapped
        elif field in {"amount", "dealamount", "value"}:
            cleaned = value.replace("$", "").replace(",", "").strip()
            props["amount"] = cleaned
        elif field in {"closedate", "close_date", "closed_ate"}:
            props["closedate"] = value
        elif field in {"dealname", "name", "company"}:
            props["dealname"] = value
        elif field.startswith("hs_") or field in {"description", "notes_last_contacted"}:
            props[field] = value
        # Ignore unknown invented fields (budget_signal, timeline, etc.) —
        # they aren't HubSpot deal properties and cause 400s.

    return props


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
