import pytest
from httpx import ASGITransport, AsyncClient

from accountflow.main import app
from accountflow.providers.registry import clear_provider_cache
from tests.conftest import register_and_login


@pytest.fixture(autouse=True)
def _clear():
    clear_provider_cache()
    yield
    clear_provider_cache()


@pytest.mark.asyncio
async def test_integrations_status(auth_env):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await register_and_login(client)
        resp = await client.get("/integrations/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "hubspot" in body
    assert "gmail" in body
    assert "jira" in body


@pytest.mark.asyncio
async def test_hubspot_pipelines_and_create_deal(auth_env, monkeypatch):
    monkeypatch.setenv("INTEGRATIONS_MOCK", "true")
    from accountflow.core.config import clear_settings_cache
    from tests.conftest import CSRF_HEADERS

    clear_settings_cache()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await register_and_login(client)
        pipes = await client.get("/integrations/hubspot/pipelines")
        assert pipes.status_code == 200
        assert pipes.json()["pipelines"][0]["stages"]

        deals = await client.get("/integrations/hubspot/deals")
        assert deals.status_code == 200
        assert len(deals.json()["deals"]) >= 2

        created = await client.post(
            "/integrations/hubspot/deals",
            headers=CSRF_HEADERS,
            json={
                "name": "Beta Industries",
                "amount": "60000",
                "stage_id": "presentationscheduled",
                "pipeline_id": "default",
            },
        )
        assert created.status_code == 200
        body = created.json()
        assert body["name"] == "Beta Industries"
        assert body["created"] is True
