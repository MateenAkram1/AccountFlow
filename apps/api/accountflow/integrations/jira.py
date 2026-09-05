import httpx

from accountflow.core.config import get_settings
from accountflow.models.schemas import ExecutionStepResult, TaskItem


class JiraClient:
    def __init__(
        self,
        project_key: str | None = None,
        *,
        site_url: str | None = None,
        email: str | None = None,
        api_token: str | None = None,
        user_id: str | None = None,
        allow_env_fallback: bool = True,
    ) -> None:
        settings = get_settings()
        self._user_id = user_id
        if site_url is not None or email is not None or api_token is not None:
            self._base = (site_url or "").rstrip("/")
            self._email = (email or "").strip()
            self._token = (api_token or "").strip()
        elif allow_env_fallback:
            self._base = (settings.jira_base_url or "").rstrip("/")
            self._email = (settings.jira_email or "").strip()
            self._token = (settings.jira_api_token or "").strip()
        else:
            self._base = ""
            self._email = ""
            self._token = ""
        # Preference order: explicit arg > saved UI selection > (optional) env
        self._project = (project_key or "").strip() or self._load_selected_project(
            user_id, allow_env_fallback=allow_env_fallback
        )

    def _auth(self) -> tuple[str, str]:
        return (self._email, self._token)

    @staticmethod
    def _load_selected_project(
        user_id: str | None = None, *, allow_env_fallback: bool = True
    ) -> str:
        from accountflow.db.tokens import get_token_store

        if user_id:
            stored = get_token_store().get(user_id, "jira") or {}
            selected = (stored.get("project_key") or "").strip()
            if selected:
                return selected
        if allow_env_fallback:
            from accountflow.core.config import get_settings

            return (get_settings().jira_project_key or "").strip()
        return ""

    @staticmethod
    def save_selected_project(
        project_key: str,
        project_name: str | None = None,
        *,
        user_id: str,
    ) -> None:
        from accountflow.db.tokens import get_token_store

        get_token_store().save(
            user_id,
            "jira",
            {
                "project_key": project_key.strip(),
                "project_name": project_name,
            },
        )

    @staticmethod
    def get_selected_project(user_id: str | None = None) -> dict | None:
        from accountflow.db.tokens import get_token_store

        if not user_id:
            return None
        stored = get_token_store().get(user_id, "jira")
        if not stored or not stored.get("project_key"):
            return None
        return {
            "key": stored.get("project_key"),
            "name": stored.get("project_name"),
        }

    async def list_projects(self) -> list[dict]:
        if not all([self._base, self._email, self._token]):
            raise ValueError("Jira credentials incomplete")
        async with httpx.AsyncClient(timeout=30.0) as client:
            # IMPORTANT: unauthenticated GET /project returns HTTP 200 + [] on Jira Cloud.
            # Always verify identity first so we don't report "no projects" on bad tokens.
            me = await client.get(
                f"{self._base}/rest/api/3/myself",
                auth=self._auth(),
                headers={"Accept": "application/json"},
            )
            if me.status_code == 401:
                raise ValueError(
                    "Jira authentication failed (401). Your API token is invalid or expired. "
                    "Create a new token at https://id.atlassian.com/manage-profile/security/api-tokens "
                    "while signed in as the same account that owns the Jira site, then update "
                    "JIRA_API_TOKEN and JIRA_EMAIL in .env (email must match that Atlassian account)."
                )
            if me.status_code >= 400:
                raise ValueError(f"Jira /myself failed HTTP {me.status_code}: {me.text[:200]}")

            projects = await self._fetch_project_rows(client)
            if projects:
                return projects

            # Fallback endpoints / params
            for params in (
                {"maxResults": 50},
                {"maxResults": 50, "status": "live"},
                {"maxResults": 50, "expand": "description"},
            ):
                projects = await self._fetch_project_rows(client, use_search=True, params=params)
                if projects:
                    return projects

            return []

    async def _fetch_project_rows(
        self,
        client: httpx.AsyncClient,
        use_search: bool = False,
        params: dict | None = None,
    ) -> list[dict]:
        if use_search:
            resp = await client.get(
                f"{self._base}/rest/api/3/project/search",
                auth=self._auth(),
                headers={"Accept": "application/json"},
                params=params or {"maxResults": 50},
            )
        else:
            resp = await client.get(
                f"{self._base}/rest/api/3/project",
                auth=self._auth(),
                headers={"Accept": "application/json"},
            )
        if resp.status_code == 401:
            raise ValueError(
                "Jira authentication failed (401). Re-create JIRA_API_TOKEN in .env"
            )
        if resp.status_code >= 400:
            return []
        data = resp.json()
        rows = data if isinstance(data, list) else (data.get("values") or [])
        return [
            {"key": p.get("key"), "name": p.get("name"), "id": p.get("id")}
            for p in rows
            if p.get("key")
        ]

    async def _create_payload(
        self, client: httpx.AsyncClient, project: str, task: TaskItem
    ) -> dict:
        """Build create-issue payload using createmeta when available."""
        issue_type: dict = {"name": "Task"}
        meta = await client.get(
            f"{self._base}/rest/api/3/issue/createmeta",
            auth=self._auth(),
            params={
                "projectKeys": project,
                "expand": "projects.issuetypes",
            },
        )
        if meta.status_code == 200:
            projects = meta.json().get("projects") or []
            if projects:
                types = projects[0].get("issuetypes") or []
                # Prefer non-subtask types
                preferred = next(
                    (
                        t
                        for t in types
                        if not t.get("subtask") and t.get("name") in {"Task", "Story", "Bug"}
                    ),
                    None,
                )
                if not preferred:
                    preferred = next((t for t in types if not t.get("subtask")), None)
                if preferred and preferred.get("id"):
                    issue_type = {"id": preferred["id"]}
                elif preferred and preferred.get("name"):
                    issue_type = {"name": preferred["name"]}

        return {
            "fields": {
                "project": {"key": project},
                "summary": task.summary[:255],
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": task.description or task.summary,
                                }
                            ],
                        }
                    ],
                },
                "issuetype": issue_type,
            }
        }

    async def _resolve_project(self, client: httpx.AsyncClient) -> tuple[str | None, str | None]:
        """Returns (project_key, error_message)."""
        # If env has a key, verify it exists; otherwise fall back to first accessible project
        if self._project:
            resp = await client.get(
                f"{self._base}/rest/api/3/project/{self._project}",
                auth=self._auth(),
            )
            if resp.status_code == 200:
                return self._project, None
            # Invalid/missing key — keep going to auto-detect

        try:
            projects = await self.list_projects()
        except ValueError as e:
            return None, str(e)
        except httpx.HTTPError as e:
            detail = (
                f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                if isinstance(e, httpx.HTTPStatusError)
                else str(e)
            )
            return None, detail
        if not projects:
            return None, (
                "No accessible Jira projects. Create a project in Jira, then select it "
                "on the Connect page."
            )
        # Do not auto-pick silently when user hasn't chosen — prefer first only as soft default
        # if nothing was selected (keeps execute working after selection UI save).
        return projects[0].get("key"), None

    async def create_issue(self, task: TaskItem) -> ExecutionStepResult:
        settings = get_settings()
        if settings.integrations_mock:
            return ExecutionStepResult(
                step="create_jira_task",
                success=True,
                external_id="MOCK-101",
                message=f"Mock created: {task.summary}",
            )

        if not all([self._base, self._email, self._token]):
            return ExecutionStepResult(
                step="create_jira_task",
                success=False,
                error="Jira configuration incomplete (JIRA_SITE_URL / EMAIL / API_TOKEN)",
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            project, resolve_err = await self._resolve_project(client)
            if not project:
                return ExecutionStepResult(
                    step="create_jira_task",
                    success=False,
                    error=resolve_err or "No Jira project found. Set JIRA_PROJECT_KEY in .env",
                )
            self._project = project
            payload = await self._create_payload(client, project, task)

            try:
                resp = await client.post(
                    f"{self._base}/rest/api/3/issue",
                    auth=self._auth(),
                    headers={"Content-Type": "application/json"},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return ExecutionStepResult(
                    step="create_jira_task",
                    success=True,
                    external_id=data.get("key"),
                    message=f"Created {data.get('key')} in {project}",
                )
            except httpx.HTTPError as e:
                detail = (
                    f"HTTP {e.response.status_code}: {e.response.text[:300]}"
                    if isinstance(e, httpx.HTTPStatusError)
                    else str(e)
                )
                return ExecutionStepResult(
                    step="create_jira_task",
                    success=False,
                    error=detail,
                )

    async def create_change_request(self, summary: str, description: str) -> ExecutionStepResult:
        task = TaskItem(
            summary=f"[CR] {summary}",
            description=description,
            evidence_quote=summary,
            confidence=1.0,
        )
        return await self.create_issue(task)

    async def ping(self) -> dict:
        if not all([self._base, self._email, self._token]):
            return {"ok": False, "error": "Jira credentials incomplete"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{self._base}/rest/api/3/myself",
                auth=self._auth(),
            )
            if resp.status_code == 401:
                return {
                    "ok": False,
                    "error": (
                        "Jira auth failed (401). Re-create API token and update JIRA_API_TOKEN"
                    ),
                }
            if resp.status_code >= 400:
                return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            me = resp.json()
            project, err = await self._resolve_project(client)
            return {
                "ok": bool(project),
                "user": me.get("displayName") or me.get("emailAddress"),
                "project_key": project,
                "error": err,
            }
