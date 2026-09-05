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
