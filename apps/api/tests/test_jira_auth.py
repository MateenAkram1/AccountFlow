import pytest

from accountflow.integrations.jira import JiraClient


@pytest.mark.asyncio
async def test_list_projects_fails_loudly_on_401(httpx_mock, monkeypatch):
    monkeypatch.setenv("JIRA_SITE_URL", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_EMAIL", "user@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "bad-token")
    from accountflow.core.config import clear_settings_cache

    clear_settings_cache()

    httpx_mock.add_response(
        url="https://example.atlassian.net/rest/api/3/myself",
        method="GET",
        status_code=401,
        text="Client must be authenticated",
    )

    with pytest.raises(ValueError, match="authentication failed"):
        await JiraClient().list_projects()
