import httpx

from accountflow.core.config import get_settings
from accountflow.models.schemas import ExecutionStepResult, TaskItem


class JiraClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._base = settings.jira_base_url.rstrip("/")
        self._email = settings.jira_email
        self._token = settings.jira_api_token
        self._project = settings.jira_project_key

    async def create_issue(self, task: TaskItem) -> ExecutionStepResult:
        settings = get_settings()
        if settings.integrations_mock:
            return ExecutionStepResult(
                step="create_jira_task",
                success=True,
                external_id="MOCK-101",
                message=f"Mock created: {task.summary}",
            )

        if not all([self._base, self._email, self._token, self._project]):
            raise ValueError("Jira configuration incomplete")

        payload = {
            "fields": {
                "project": {"key": self._project},
                "summary": task.summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": task.description}],
                        }
                    ],
                },
                "issuetype": {"name": "Task"},
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(
                        f"{self._base}/rest/api/3/issue",
                        auth=(self._email, self._token),
                        headers={"Content-Type": "application/json"},
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return ExecutionStepResult(
                        step="create_jira_task",
                        success=True,
                        external_id=data.get("key"),
                        message=f"Created {data.get('key')}",
                    )
                except httpx.HTTPError as e:
                    if attempt == 2:
                        return ExecutionStepResult(
                            step="create_jira_task",
                            success=False,
                            error=str(e),
                        )
        return ExecutionStepResult(step="create_jira_task", success=False, error="Unknown error")

    async def create_change_request(self, summary: str, description: str) -> ExecutionStepResult:
        task = TaskItem(
            summary=f"[CR] {summary}",
            description=description,
            evidence_quote=summary,
            confidence=1.0,
        )
        return await self.create_issue(task)
