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

    async def list_deals(self, limit: int = 100) -> list[dict]:
        if not self._token:
            raise ValueError("HubSpot token missing")
        headers = {"Authorization": f"Bearer {self._token}"}
        deals: list[dict] = []
        after: str | None = None
        async with httpx.AsyncClient(timeout=30.0) as client:
            while len(deals) < limit:
                params: dict[str, str | int] = {
                    "limit": min(100, limit - len(deals)),
                    "properties": "dealname,dealstage,amount,closedate,pipeline",
                }
                if after:
                    params["after"] = after
                resp = await client.get(
                    f"{self._base}/crm/v3/objects/deals",
                    headers=headers,
                    params=params,
                )
                resp.raise_for_status()
                payload = resp.json()
                for row in payload.get("results", []):
                    props = row.get("properties", {})
                    deals.append(
                        {
                            "id": row.get("id"),
                            "name": props.get("dealname") or f"Deal {row.get('id')}",
                            "stage": props.get("dealstage"),
                            "amount": props.get("amount"),
                            "close_date": props.get("closedate"),
                            "pipeline": props.get("pipeline"),
                        }
                    )
                after = (payload.get("paging") or {}).get("next", {}).get("after")
                if not after:
                    break
            return deals

    async def list_pipelines(self) -> list[dict]:
        """Return deal pipelines with stages (labels + HubSpot stage IDs)."""
        settings = get_settings()
        if settings.integrations_mock:
            return _mock_pipelines()
        if not self._token:
            raise ValueError("HubSpot token missing")
        headers = {"Authorization": f"Bearer {self._token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self._base}/crm/v3/pipelines/deals",
                headers=headers,
            )
            resp.raise_for_status()
            pipelines = []
            for pipe in resp.json().get("results", []):
                stages = []
                for stage in sorted(
                    pipe.get("stages", []),
                    key=lambda s: s.get("displayOrder", 0),
                ):
                    stages.append(
                        {
                            "id": stage.get("id"),
                            "label": stage.get("label") or stage.get("id"),
                            "display_order": stage.get("displayOrder"),
                            "metadata": stage.get("metadata") or {},
                        }
                    )
                pipelines.append(
                    {
                        "id": pipe.get("id"),
                        "label": pipe.get("label") or pipe.get("id"),
                        "display_order": pipe.get("displayOrder"),
                        "stages": stages,
                    }
                )
            pipelines.sort(key=lambda p: p.get("display_order") or 0)
            return pipelines

    async def create_deal(
        self,
        *,
        name: str,
        amount: str | None = None,
        stage_id: str | None = None,
        pipeline_id: str | None = None,
        close_date: str | None = None,
    ) -> dict:
        """Always create a new HubSpot deal (does not reuse an existing one)."""
        settings = get_settings()
        if settings.integrations_mock:
            return {
                "id": f"demo-{name[:12].replace(' ', '-').lower() or 'new'}",
                "name": name,
                "stage": stage_id or "appointmentscheduled",
                "amount": amount,
                "pipeline": pipeline_id or "default",
                "created": True,
            }
        if not self._token:
            raise ValueError("HubSpot token missing")

        deal_name = (name or "").strip() or "AccountFlow deal"
        properties: dict[str, str] = {"dealname": deal_name}
        if amount and str(amount).strip():
            properties["amount"] = str(amount).replace("$", "").replace(",", "").strip()
        if stage_id and stage_id.strip():
            properties["dealstage"] = stage_id.strip()
        if pipeline_id and pipeline_id.strip():
            properties["pipeline"] = pipeline_id.strip()
        if close_date and close_date.strip():
            properties["closedate"] = close_date.strip()

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base}/crm/v3/objects/deals",
                headers=headers,
                json={"properties": properties},
            )
            if resp.status_code >= 400 and "pipeline" in properties:
                # Some portals reject unknown pipeline ids — retry without it
                properties.pop("pipeline", None)
                resp = await client.post(
                    f"{self._base}/crm/v3/objects/deals",
                    headers=headers,
                    json={"properties": properties},
                )
            resp.raise_for_status()
            data = resp.json()
            props = data.get("properties", {})
            return {
                "id": data.get("id"),
                "name": props.get("dealname") or deal_name,
                "stage": props.get("dealstage"),
                "amount": props.get("amount"),
                "pipeline": props.get("pipeline"),
                "created": True,
            }

    async def ensure_demo_deal(self) -> dict:
        """Create a sample deal for demos (always creates a new deal)."""
        return await self.create_deal(
            name="AccountFlow OS — Acme Corp",
            amount="40000",
            stage_id="appointmentscheduled",
            pipeline_id="default",
        )

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
                # Best-effort aliases for LLM-invented labels
                if "propos" in stage_key or "present" in stage_key:
                    mapped = "presentationscheduled"
                elif "close" in stage_key and "won" in stage_key:
                    mapped = "closedwon"
                else:
                    # Trust HubSpot stage IDs from pipeline dropdowns (custom pipelines)
                    mapped = value
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


def _mock_pipelines() -> list[dict]:
    return [
        {
            "id": "default",
            "label": "Sales Pipeline",
            "display_order": 0,
            "stages": [
                {"id": "appointmentscheduled", "label": "Appointment Scheduled", "display_order": 0},
                {"id": "qualifiedtobuy", "label": "Qualified To Buy", "display_order": 1},
                {"id": "presentationscheduled", "label": "Presentation Scheduled", "display_order": 2},
                {"id": "decisionmakerboughtin", "label": "Decision Maker Bought-In", "display_order": 3},
                {"id": "contractsent", "label": "Contract Sent", "display_order": 4},
                {"id": "closedwon", "label": "Closed Won", "display_order": 5},
                {"id": "closedlost", "label": "Closed Lost", "display_order": 6},
            ],
        }
    ]


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
