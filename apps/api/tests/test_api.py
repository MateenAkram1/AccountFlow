import pytest
from httpx import ASGITransport, AsyncClient

from accountflow.main import app
from tests.conftest import CSRF_HEADERS, register_and_login


@pytest.mark.asyncio
async def test_health(auth_env):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_runs_require_auth(auth_env):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/runs")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_run_with_transcript(authed_client):
    account = (
        '{"deal_id":"demo-001","company":"Acme Corp","stage":"discovery",'
        '"contacts":[{"name":"Sarah","role":"CTO","email":"sarah@acme.example"}]}'
    )
    resp = await authed_client.post(
        "/runs",
        data={
            "transcript": "Let's finalize the API spec and send documentation by Friday.",
            "account_json": account,
        },
        headers=CSRF_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "awaiting_approval"
    assert body["action_package"] is not None
    assert body["user_id"]


@pytest.mark.asyncio
async def test_create_run_skips_scope_without_sow(authed_client):
    account = (
        '{"deal_id":"demo-001","company":"Acme Corp","stage":"discovery",'
        '"contacts":[{"name":"Sarah","role":"CTO","email":"sarah@acme.example"}]}'
    )
    resp = await authed_client.post(
        "/runs",
        data={
            "transcript": "Let's finalize the API spec and send documentation by Friday.",
            "account_json": account,
        },
        headers=CSRF_HEADERS,
    )
    body = resp.json()
    scope_report = body["action_package"]["scope_report"]
    assert scope_report["skipped"] is True
    assert scope_report["flags"] == []


@pytest.mark.asyncio
async def test_resume_requires_at_least_one_section(authed_client):
    account = (
        '{"deal_id":"demo-001","company":"Acme Corp","stage":"discovery",'
        '"contacts":[{"name":"Sarah","role":"CTO","email":"sarah@acme.example"}]}'
    )
    create = await authed_client.post(
        "/runs",
        data={
            "transcript": "Let's finalize the API spec and send documentation by Friday.",
            "account_json": account,
        },
        headers=CSRF_HEADERS,
    )
    run_id = create.json()["id"]
    resp = await authed_client.post(
        f"/runs/{run_id}/resume",
        json={
            "emails": [],
            "crm_updates": [],
            "tasks": [],
            "sections": {"emails": False, "crm": False, "tasks": False},
        },
        headers=CSRF_HEADERS,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_resume_partial_sections(authed_client):
    account = (
        '{"deal_id":"demo-001","company":"Acme Corp","stage":"discovery",'
        '"contacts":[{"name":"Sarah","role":"CTO","email":"sarah@acme.example"}]}'
    )
    create = await authed_client.post(
        "/runs",
        data={
            "transcript": "Let's finalize the API spec and send documentation by Friday.",
            "account_json": account,
        },
        headers=CSRF_HEADERS,
    )
    body = create.json()
    run_id = body["id"]
    email = body["action_package"]["emails"][0]
    resp = await authed_client.post(
        f"/runs/{run_id}/resume",
        json={
            "emails": [email],
            "crm_updates": [],
            "tasks": [],
            "sections": {
                "emails": True,
                "crm": False,
                "tasks": False,
                "workflow": "client_followup",
            },
        },
        headers=CSRF_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["approved"]["sections"]["emails"] is True
    assert resp.json()["approved"]["sections"]["crm"] is False


@pytest.mark.asyncio
async def test_create_run_rejects_garbled(authed_client):
    account = '{"deal_id":"demo-001","company":"Acme","stage":"discovery"}'
    resp = await authed_client.post(
        "/runs",
        data={"transcript": "asdf jkl qwer tyui", "account_json": account},
        headers=CSRF_HEADERS,
    )
    assert resp.status_code == 400
