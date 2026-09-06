"""Integration status + live connectivity checks (per-user BYOK)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from accountflow.api.deps import CurrentUser, get_current_user, require_csrf
from accountflow.core.config import get_settings
from accountflow.core.security import redact_text
from accountflow.integrations.jira import JiraClient
from accountflow.services.credentials import (
    CredentialsMissing,
    gmail_client_for_user,
    hubspot_client_for_user,
    integration_status_for_user,
    jira_client_for_user,
)

router = APIRouter(prefix="/integrations", tags=["integrations"])


class SelectJiraProjectRequest(BaseModel):
    project_key: str
    project_name: str | None = None


@router.get("/status")
async def integrations_status(user: CurrentUser = Depends(get_current_user)):
    return integration_status_for_user(user.id)


@router.get("/ping")
async def integrations_ping(user: CurrentUser = Depends(get_current_user)):
    settings = get_settings()
    results: dict = {"mock_mode": settings.integrations_mock}

    if settings.integrations_mock:
        results["note"] = "INTEGRATIONS_MOCK=true — live calls skipped"
        return results

    try:
        results["hubspot"] = await hubspot_client_for_user(user.id).ping()
    except CredentialsMissing as e:
        results["hubspot"] = {"ok": False, "error": str(e)}
    except Exception as e:
        results["hubspot"] = {"ok": False, "error": redact_text(str(e))}

    try:
        results["gmail"] = await gmail_client_for_user(user.id).ping()
    except Exception as e:
        results["gmail"] = {"ok": False, "error": redact_text(str(e))}

    try:
        results["jira"] = await jira_client_for_user(user.id).ping()
    except CredentialsMissing as e:
        results["jira"] = {"ok": False, "error": str(e)}
    except Exception as e:
        results["jira"] = {"ok": False, "error": redact_text(str(e))}
    return results


@router.get("/hubspot/deals")
async def list_hubspot_deals(user: CurrentUser = Depends(get_current_user)):
    settings = get_settings()
    if settings.integrations_mock:
        return {
            "deals": [
                {
                    "id": "demo-001",
                    "name": "Acme Corp (mock)",
                    "stage": "appointmentscheduled",
                    "amount": "40000",
                    "pipeline": "default",
                },
                {
                    "id": "demo-002",
                    "name": "Meridian CareOps (mock)",
                    "stage": "qualifiedtobuy",
                    "amount": "120000",
                    "pipeline": "default",
                },
            ]
        }
    try:
        deals = await hubspot_client_for_user(user.id).list_deals(limit=100)
        return {"deals": deals}
    except CredentialsMissing as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=redact_text(str(e))) from e


class CreateHubSpotDealRequest(BaseModel):
    name: str
    amount: str | None = None
    stage_id: str | None = None
    pipeline_id: str | None = None
    close_date: str | None = None


@router.get("/hubspot/pipelines")
async def list_hubspot_pipelines(user: CurrentUser = Depends(get_current_user)):
    """Deal pipelines + stages from HubSpot (for CRM dropdowns)."""
    try:
        pipelines = await hubspot_client_for_user(user.id).list_pipelines()
        return {"pipelines": pipelines}
    except CredentialsMissing as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=redact_text(str(e))) from e


@router.post("/hubspot/deals")
async def create_hubspot_deal(
    body: CreateHubSpotDealRequest,
    user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    """Create a new HubSpot deal and return it."""
    if not (body.name or "").strip():
        raise HTTPException(status_code=400, detail="Deal name is required")
    try:
        deal = await hubspot_client_for_user(user.id).create_deal(
            name=body.name.strip(),
            amount=body.amount,
            stage_id=body.stage_id,
            pipeline_id=body.pipeline_id,
            close_date=body.close_date,
        )
        return deal
    except CredentialsMissing as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=redact_text(str(e))) from e


@router.post("/hubspot/deals/ensure")
async def ensure_hubspot_deal(
    user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    """Create a sample HubSpot deal (always creates a new deal)."""
    settings = get_settings()
    if settings.integrations_mock:
        return {
            "id": "demo-001",
            "name": "Acme Corp (mock)",
            "stage": "appointmentscheduled",
            "amount": "40000",
            "created": True,
        }
    try:
        deal = await hubspot_client_for_user(user.id).ensure_demo_deal()
        return deal
    except CredentialsMissing as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=redact_text(str(e))) from e


@router.get("/jira/projects")
async def list_jira_projects(user: CurrentUser = Depends(get_current_user)):
    settings = get_settings()
    if settings.integrations_mock:
        return {
            "projects": [{"key": "DEMO", "name": "Demo (mock)"}],
            "selected": {"key": "DEMO", "name": "Demo (mock)"},
        }
    try:
        client = jira_client_for_user(user.id)
        projects = await client.list_projects()
        return {
            "projects": projects,
            "selected": JiraClient.get_selected_project(user.id),
        }
    except CredentialsMissing as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=401, detail=redact_text(str(e))) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=redact_text(str(e))) from e


@router.put("/jira/project")
async def select_jira_project(
    body: SelectJiraProjectRequest,
    user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    if not body.project_key.strip():
        raise HTTPException(status_code=400, detail="project_key is required")
    JiraClient.save_selected_project(body.project_key, body.project_name, user_id=user.id)
    return {"ok": True, "selected": JiraClient.get_selected_project(user.id)}


@router.get("/jira/project")
async def get_selected_jira_project(user: CurrentUser = Depends(get_current_user)):
    return {"selected": JiraClient.get_selected_project(user.id)}
