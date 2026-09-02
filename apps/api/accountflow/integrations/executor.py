from datetime import datetime

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
from accountflow.db.store import get_run_store


class WorkflowExecutor:
    def __init__(
        self,
        hubspot_token: str | None = None,
        gmail_token: str | None = None,
    ) -> None:
        self._hubspot = HubSpotClient(hubspot_token)
        self._gmail = GmailClient(gmail_token)
        self._jira = JiraClient()

    async def execute(self, run: RunRecord, approved: ApprovedPayload) -> ExecutionLog:
        steps: list[ExecutionStepResult] = []
        workflow = approved.sections.workflow or "client_followup"

        if workflow == "change_request":
            steps.extend(await self._run_change_request(run, approved))
        else:
            steps.extend(await self._run_client_followup(run, approved))

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
        package = approved

        if approved.sections.emails and package.emails:
            for email in package.emails:
                steps.append(await self._gmail.send(email))

        if approved.sections.crm and package.crm_updates and run.account:
            steps.append(
                await self._hubspot.update_deal(run.account.deal_id, package.crm_updates)
            )

        if approved.sections.tasks and package.tasks:
            for task in package.tasks:
                steps.append(await self._jira.create_issue(task))

        return steps

    async def _run_change_request(
        self, run: RunRecord, approved: ApprovedPayload
    ) -> list[ExecutionStepResult]:
        steps: list[ExecutionStepResult] = []
        scope = run.action_package.scope_report if run.action_package else None
        if scope:
            for flag in scope.flags:
                if flag.recommended_workflow == "change_request":
                    steps.append(
                        await self._jira.create_change_request(
                            flag.request,
                            f"Evidence: {flag.evidence_quote}",
                        )
                    )
        if run.account and approved.crm_updates:
            steps.append(
                await self._hubspot.update_deal(run.account.deal_id, approved.crm_updates)
            )
        return steps
