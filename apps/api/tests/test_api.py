import os

import pytest
from httpx import ASGITransport, AsyncClient

from accountflow.main import app


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("STT_PROVIDER", "mock")
    monkeypatch.setenv("INTEGRATIONS_MOCK", "true")


@pytest.mark.asyncio
async def test_health(mock_env):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_run_with_transcript(mock_env):
    account = (
        '{"deal_id":"demo-001","company":"Acme Corp","stage":"discovery",'
        '"contacts":[{"name":"Sarah","role":"CTO","email":"sarah@acme.example"}]}'
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/runs",
            data={
                "transcript": "Let's finalize the API spec and send documentation by Friday.",
                "account_json": account,
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "awaiting_approval"
    assert body["action_package"] is not None


@pytest.mark.asyncio
async def test_create_run_rejects_garbled(mock_env):
    account = '{"deal_id":"demo-001","company":"Acme","stage":"discovery"}'
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/runs",
            data={"transcript": "asdf jkl qwer tyui", "account_json": account},
        )
    assert resp.status_code == 400
