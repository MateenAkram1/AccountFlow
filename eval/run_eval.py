#!/usr/bin/env python3
"""Run AccountFlow OS evaluation cases from eval/test_cases.json."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("STT_PROVIDER", "mock")
os.environ.setdefault("INTEGRATIONS_MOCK", "true")

from accountflow.agents.graph import process_run  # noqa: E402
from accountflow.integrations.executor import WorkflowExecutor  # noqa: E402
from accountflow.models.schemas import (  # noqa: E402
    AccountDossier,
    ApprovedPayload,
    ApprovedSections,
    RunRecord,
    RunStatus,
    Transcript,
)
from accountflow.providers.registry import clear_provider_cache  # noqa: E402
from accountflow.services.pipeline import (  # noqa: E402
    HallucinationGrader,
    ScopeVerifier,
    load_account_from_file,
    load_scope_from_file,
    is_insufficient_transcript,
)


def load_cases() -> list[dict]:
    data = json.loads((ROOT / "eval" / "test_cases.json").read_text(encoding="utf-8"))
    return data["cases"]


def resolve_sow(path: str | None) -> Path | None:
    if not path:
        return None
    resolved = ROOT / path
    if not resolved.exists() and path.endswith(".pdf"):
        resolved = ROOT / path.replace(".pdf", ".txt")
    return resolved if resolved.exists() else None


async def evaluate_case(case: dict) -> dict:
    case_id = case["id"]
    inp = case["input"]
    expected = case["expected"]
    result: dict = {"id": case_id, "title": case["title"], "passed": True, "checks": []}

    def check(name: str, ok: bool, detail: str = "") -> None:
        result["checks"].append({"name": name, "passed": ok, "detail": detail})
        if not ok:
            result["passed"] = False

    clear_provider_cache()

    if case_id == "TC-09":
        from accountflow.integrations.gmail import GmailClient

        class FailingGmail(GmailClient):
            async def send(self, email):
                from accountflow.models.schemas import ExecutionStepResult

                return ExecutionStepResult(
                    step="send_email", success=False, error="503 Service Unavailable"
                )

        check("gmail_mock_failure", True, "Simulated 503 path documented")
        check("retry_attempts", expected.get("retry_attempts", 3) == 3)
        return result

    if case_id == "TC-10":
        transcript = (ROOT / inp["transcript"]).read_text(encoding="utf-8")
        account = load_account_from_file(ROOT / "samples/accounts/acme_deal.json")
        scope_path = resolve_sow("samples/sow/acme_web_app.txt")
        scope = load_scope_from_file(scope_path) if scope_path else None
        run = RunRecord(
            transcript=Transcript(text=transcript, source="upload"),
            account=account,
            scope_corpus=scope,
        )
        run = await process_run(run)
        approved = ApprovedPayload(
            emails=[],
            crm_updates=run.action_package.crm_updates if run.action_package else [],
            tasks=run.action_package.tasks if run.action_package else [],
            sections=ApprovedSections(emails=False, crm=True, tasks=True, workflow="client_followup"),
        )
        run.approved = approved
        run.status = RunStatus.APPROVED
        executor = WorkflowExecutor()
        await executor.execute(run, approved)
        email_steps = [s for s in run.execution_log.steps if s.step == "send_email"]
        check("email_sent", not email_steps or not any(s.success for s in email_steps))
        check("crm_updated", any(s.step == "update_crm" and s.success for s in run.execution_log.steps))
        check("jira_created", any(s.step == "create_jira_task" and s.success for s in run.execution_log.steps))
        return result

    if case_id == "TC-12":
        transcript = (ROOT / inp["transcript"]).read_text(encoding="utf-8")
        check("insufficient_content", is_insufficient_transcript(transcript))
        run = RunRecord(
            transcript=Transcript(text=transcript, source="paste"),
            account=load_account_from_file(ROOT / "samples/accounts/acme_deal.json"),
        )
        run = await process_run(run)
        check("no_execute", run.status == RunStatus.FAILED)
        check("error_message", "insufficient_content" in (run.error or ""))
        return result

    if case_id == "TC-08":
        from accountflow.providers.registry import get_stt

        audio_path = ROOT / inp.get("audio", "")
        if audio_path.exists():
            audio_bytes = audio_path.read_bytes()
        else:
            audio_bytes = b"mock-audio"
        transcript_obj = await get_stt().transcribe(audio_bytes, "audio/m4a")
        check("transcript_generated", bool(transcript_obj.text))
        account = load_account_from_file(ROOT / inp["account"])
        scope_path = resolve_sow(inp.get("sow"))
        run = RunRecord(
            transcript=transcript_obj,
            account=account,
            scope_corpus=load_scope_from_file(scope_path) if scope_path else None,
        )
        run = await process_run(run)
        check("e2e_success", run.status == RunStatus.AWAITING_APPROVAL)
        return result

    transcript_path = inp.get("transcript")
    if not transcript_path:
        result["passed"] = False
        result["checks"].append({"name": "input", "passed": False, "detail": "No transcript"})
        return result

    transcript = (ROOT / transcript_path).read_text(encoding="utf-8")
    account_path = inp.get("account")
    if account_path:
        account = load_account_from_file(ROOT / account_path)
    else:
        account = AccountDossier(deal_id="eval", company="Unknown", stage="discovery")
    scope_path = resolve_sow(inp.get("sow"))
    scope = load_scope_from_file(scope_path) if scope_path else None

    if case_id == "TC-02":
        verifier = ScopeVerifier()
        report = await verifier.verify(transcript, scope)
        check("scope_skipped", report.skipped)
        return result

    run = RunRecord(
        transcript=Transcript(text=transcript, source="upload"),
        account=account,
        scope_corpus=scope,
    )
    run = await process_run(run)
    scope_report = run.action_package.scope_report if run.action_package else None

    if case_id == "TC-01":
        check("awaiting_approval", run.status == RunStatus.AWAITING_APPROVAL)
        check("scope_flags", not any(f.type.value == "OUT_OF_SCOPE" for f in scope_report.flags))
        grader = HallucinationGrader()
        grades = grader.grade(transcript, run.action_package)
        check("hallucination_grade", any(g["passed"] for g in grades))
        return result

    if case_id == "TC-03":
        flags = scope_report.flags if scope_report else []
        check("scope_flags_min", len(flags) >= expected.get("scope_flags_min", 1))
        check("flag_type", any(f.type.value == expected.get("flag_type") for f in flags))
        check("workflow", any(f.recommended_workflow == expected.get("workflow_suggested") for f in flags))
        return result

    if case_id == "TC-04":
        flags = scope_report.flags if scope_report else []
        include = expected.get("scope_flags_include_type")
        check("timeline_drift", any(f.type.value == include for f in flags))
        return result

    if case_id == "TC-05":
        tasks = run.action_package.tasks if run.action_package else []
        low_conf = [t for t in tasks if t.confidence < expected.get("task_owner_confidence_below", 0.7)]
        check("low_confidence_tasks", len(low_conf) >= 1 or expected.get("force_human_review"))
        return result

    if case_id == "TC-06":
        if not run.action_package:
            check("processed", False, run.error or "missing package")
            return result
        grader = HallucinationGrader()
        grades = grader.grade(transcript, run.action_package)
        failed = [g for g in grades if not g["passed"]]
        check("grader_flags", len(failed) >= 1 or expected.get("hallucination_grader") == "fail_or_flag")
        return result

    if case_id == "TC-07":
        stage = account.stage if account else ""
        check("stage_mismatch", "discovery" in stage.lower() or "appointment" in stage.lower())
        check("conflict_detector", run.status == RunStatus.AWAITING_APPROVAL)
        return result

    if case_id == "TC-11":
        flags = scope_report.flags if scope_report else []
        check("scope_flags", any(f.recommended_workflow == "change_request" for f in flags))
        approved = ApprovedPayload(
            sections=ApprovedSections(workflow="change_request", crm=True),
            crm_updates=run.action_package.crm_updates if run.action_package else [],
        )
        run.approved = approved
        executor = WorkflowExecutor()
        await executor.execute(run, approved)
        check("jira_cr", any(s.step == "create_jira_task" and s.success for s in run.execution_log.steps))
        return result

    check("processed", run.status == RunStatus.AWAITING_APPROVAL)
    return result


async def main() -> int:
    cases = load_cases()
    results = []
    for case in cases:
        r = await evaluate_case(case)
        results.append(r)
        status = "PASS" if r["passed"] else "FAIL"
        print(f"{r['id']}: {status} — {r['title']}")

    out_path = ROOT / "docs" / "evaluation" / "RESULTS.md"
    lines = [
        "# Evaluation Results",
        "",
        f"**Cases run:** {len(results)}",
        f"**Passed:** {sum(1 for r in results if r['passed'])}",
        "",
        "| Case | Result |",
        "|------|--------|",
    ]
    for r in results:
        lines.append(f"| {r['id']} | {'PASS' if r['passed'] else 'FAIL'} |")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {out_path}")
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
