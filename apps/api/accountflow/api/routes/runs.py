import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from accountflow.agents.graph import process_run
from accountflow.core.config import ROOT_DIR
from accountflow.db.store import get_run_store
from accountflow.integrations.executor import WorkflowExecutor
from accountflow.integrations.hubspot import HubSpotClient
from accountflow.models.schemas import (
    AccountDossier,
    ApprovedPayload,
    RunRecord,
    RunStatus,
    ScopeCorpus,
    Transcript,
)
from accountflow.providers.registry import get_stt
from accountflow.services.pipeline import load_account_from_file, load_scope_from_file, is_insufficient_transcript

router = APIRouter(prefix="/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    transcript: str | None = None
    deal_id: str | None = None
    account: AccountDossier | None = None
    scope_text: str | None = None


@router.post("", response_model=RunRecord)
async def create_run(
    transcript: str | None = Form(None),
    deal_id: str | None = Form(None),
    account_json: str | None = Form(None),
    scope_text: str | None = Form(None),
    audio: UploadFile | None = File(None),
):
    store = get_run_store()
    run = RunRecord()

    if audio:
        audio_bytes = await audio.read()
        stt = get_stt()
        try:
            transcript_obj = await stt.transcribe(audio_bytes, audio.content_type or "audio/webm")
            run.transcript = transcript_obj
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
    elif transcript:
        if is_insufficient_transcript(transcript):
            raise HTTPException(
                status_code=400,
                detail="insufficient_content: transcript lacks usable meeting content",
            )
        run.transcript = Transcript(text=transcript, source="paste")
    else:
        raise HTTPException(status_code=400, detail="Provide transcript or audio")

    if account_json:
        run.account = AccountDossier.model_validate_json(account_json)
    elif deal_id:
        hubspot = HubSpotClient()
        run.account = await hubspot.get_deal(deal_id)
    else:
        raise HTTPException(status_code=400, detail="Provide account_json or deal_id")

    if scope_text:
        run.scope_corpus = ScopeCorpus(source="inline", raw_text=scope_text, items=[])
    else:
        sow_path = ROOT_DIR / "samples" / "sow" / "acme_web_app.txt"
        if sow_path.exists():
            run.scope_corpus = load_scope_from_file(sow_path)

    try:
        run = await process_run(run)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    store.save(run)
    return run


@router.get("", response_model=list[RunRecord])
async def list_runs():
    return get_run_store().list_runs()


@router.get("/{run_id}", response_model=RunRecord)
async def get_run(run_id: str):
    run = get_run_store().get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/{run_id}/resume", response_model=RunRecord)
async def resume_run(run_id: str, approved: ApprovedPayload):
    run = get_run_store().get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != RunStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Run is not awaiting approval")

    run.approved = approved
    run.status = RunStatus.APPROVED
    get_run_store().save(run)
    return run


@router.post("/{run_id}/execute", response_model=RunRecord)
async def execute_run(run_id: str):
    run = get_run_store().get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if not run.approved:
        raise HTTPException(status_code=400, detail="Run must be approved first")

    package = run.action_package
    approved = run.approved
    if package:
        if approved.emails is None:
            approved.emails = package.emails
        if approved.crm_updates is None:
            approved.crm_updates = package.crm_updates
        if approved.tasks is None:
            approved.tasks = package.tasks

    run.status = RunStatus.EXECUTING
    get_run_store().save(run)

    executor = WorkflowExecutor()
    await executor.execute(run, approved)
    return run


@router.post("/from-sample/{case_id}", response_model=RunRecord)
async def create_from_sample(case_id: str):
    """Load a test case from eval/test_cases.json for demo/eval."""
    cases_path = ROOT_DIR / "eval" / "test_cases.json"
    data = json.loads(cases_path.read_text(encoding="utf-8"))
    case = next((c for c in data["cases"] if c["id"] == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail="Test case not found")

    inp = case["input"]
    transcript = ""
    if inp.get("transcript"):
        transcript = (ROOT_DIR / inp["transcript"]).read_text(encoding="utf-8")
    elif inp.get("audio"):
        stt = get_stt()
        audio_bytes = (ROOT_DIR / inp["audio"]).read_bytes()
        transcript_obj = await stt.transcribe(audio_bytes, "audio/m4a")
        transcript = transcript_obj.text

    account = None
    if inp.get("account"):
        account = load_account_from_file(ROOT_DIR / inp["account"])
    elif inp.get("deal_id"):
        hubspot = HubSpotClient()
        account = await hubspot.get_deal(inp["deal_id"])
    else:
        account = AccountDossier(deal_id="eval", company="Unknown", stage="discovery")

    scope = None
    sow_path = inp.get("sow")
    if sow_path:
        resolved = ROOT_DIR / sow_path
        if not resolved.exists() and sow_path.endswith(".pdf"):
            resolved = ROOT_DIR / sow_path.replace(".pdf", ".txt")
        if resolved.exists():
            scope = load_scope_from_file(resolved)

    run = RunRecord(
        transcript=Transcript(text=transcript, source="upload"),
        account=account,
        scope_corpus=scope,
    )
    try:
        run = await process_run(run)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    get_run_store().save(run)
    return run
