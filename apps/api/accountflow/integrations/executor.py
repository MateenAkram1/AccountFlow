from datetime import datetime

from accountflow.db.store import get_run_store
from accountflow.integrations.gmail import GmailClient
from accountflow.integrations.hubspot import HubSpotClient
from accountflow.integrations.jira import JiraClient
from accountflow.models.schemas import (
    ApprovedPayload,
    ExecutionLog,
    ExecutionStepResult,
    RunRecord,
    RunStatus,
)


class WorkflowExecutor:
    def __init__(
        self,
        *,
        hubspot: HubSpotClient | None = None,
        gmail: GmailClient | None = None,
        jira: JiraClient | None = None,
        user_id: str | None = None,
        hubspot_token: str | None = None,
        gmail_token: str | None = None,
    ) -> None:
        self._user_id = user_id
        self._hubspot = hubspot or HubSpotClient(hubspot_token)
        self._gmail = gmail or GmailClient(gmail_token, user_id=user_id)
        self._jira = jira or JiraClient(user_id=user_id)

    async def execute(self, run: RunRecord, approved: ApprovedPayload) -> ExecutionLog:
        steps: list[ExecutionStepResult] = []
        workflow = approved.sections.workflow or "client_followup"

        if workflow == "change_request":
            steps.extend(await self._run_change_request(run, approved))
        else:
            steps.extend(await self._run_client_followup(run, approved))

        if not steps:
            steps.append(
                ExecutionStepResult(
                    step="execute",
                    success=False,
                    error="No approved sections to execute",
                )
            )

        log = ExecutionLog(
            run_id=run.id,
            steps=steps,
            completed_at=datetime.now(),
        )
        run.execution_log = log
        run.status = RunStatus.COMPLETED if all(s.success for s in steps) else RunStatus.FAILED
        get_run_store().save(run)
        return log

    async def _run_client_followup(
        self, run: RunRecord, approved: ApprovedPayload
    ) -> list[ExecutionStepResult]:
        steps: list[ExecutionStepResult] = []

        if approved.sections.emails and approved.emails:
            for email in approved.emails:
                steps.append(await self._gmail.send(email))

        if approved.sections.crm and approved.crm_updates and run.account:
            steps.append(
                await self._hubspot.update_deal(run.account.deal_id, approved.crm_updates)
            )

        if approved.sections.tasks and approved.tasks:
            project_key = (
                approved.jira_project_key
                or approved.sections.jira_project_key
                or None
            )
            jira = (
                JiraClient(
                    project_key=project_key,
                    site_url=self._jira._base,
                    email=self._jira._email,
                    api_token=self._jira._token,
                    user_id=self._user_id,
                    allow_env_fallback=False,
                )
                if self._user_id
                else JiraClient(project_key=project_key, user_id=self._user_id)
            )
            for task in approved.tasks:
                steps.append(await jira.create_issue(task))

        return steps

    async def _run_change_request(
        self, run: RunRecord, approved: ApprovedPayload
    ) -> list[ExecutionStepResult]:
        steps: list[ExecutionStepResult] = []
        scope = run.action_package.scope_report if run.action_package else None
        project_key = (
            approved.jira_project_key
            or approved.sections.jira_project_key
            or None
        )
        jira = (
            JiraClient(
                project_key=project_key,
                site_url=self._jira._base,
                email=self._jira._email,
                api_token=self._jira._token,
                user_id=self._user_id,
                allow_env_fallback=False,
            )
            if self._user_id
            else JiraClient(project_key=project_key, user_id=self._user_id)
        )
        if scope:
            for flag in scope.flags:
                if flag.recommended_workflow == "change_request":
                    steps.append(
                        await jira.create_change_request(
                            flag.request,
                            f"Evidence: {flag.evidence_quote}",
                        )
                    )
        if approved.sections.crm and approved.crm_updates and run.account:
            steps.append(
                await self._hubspot.update_deal(run.account.deal_id, approved.crm_updates)
            )
        return steps
