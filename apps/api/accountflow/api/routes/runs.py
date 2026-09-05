import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from accountflow.agents.graph import process_run
from accountflow.api.deps import CurrentUser, get_current_user, require_csrf
from accountflow.core.config import ROOT_DIR
from accountflow.core.security import redact_text
from accountflow.db.sows import get_sow_store
from accountflow.db.store import get_run_store
from accountflow.integrations.executor import WorkflowExecutor
from accountflow.models.schemas import (
    AccountDossier,
    ApprovedPayload,
    RunRecord,
    RunStatus,
    ScopeCorpus,
    Transcript,
)
from accountflow.services.credentials import (
    CredentialsMissing,
    gmail_client_for_user,
    hubspot_client_for_user,
    jira_client_for_user,
    llm_for_user,
    stt_for_user,
)
from accountflow.services.documents import extract_text_from_bytes
from accountflow.services.llm_context import llm_override
from accountflow.services.pipeline import load_account_from_file, load_scope_from_file, is_insufficient_transcript

router = APIRouter(prefix="/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    transcript: str | None = None
    deal_id: str | None = None
    account: AccountDossier | None = None
    scope_text: str | None = None


def _http_from_creds(exc: Exception) -> HTTPException:
    msg = redact_text(str(exc))
    if isinstance(exc, CredentialsMissing):
        return HTTPException(status_code=400, detail=msg)
    return HTTPException(status_code=502, detail=msg)


@router.post("", response_model=RunRecord)
async def create_run(
    transcript: str | None = Form(None),
    deal_id: str | None = Form(None),
    account_json: str | None = Form(None),
    scope_text: str | None = Form(None),
    sow_id: str | None = Form(None),
    audio: UploadFile | None = File(None),
    transcript_file: UploadFile | None = File(None),
    sow_file: UploadFile | None = File(None),
    user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    store = get_run_store()
    run = RunRecord(user_id=user.id)

    if audio and audio.filename:
        audio_bytes = await audio.read()
        try:
            stt = stt_for_user(user.id)
            transcript_obj = await stt.transcribe(audio_bytes, audio.content_type or "audio/webm")
            run.transcript = transcript_obj
        except CredentialsMissing as e:
            raise _http_from_creds(e) from e
        except ValueError as e:
            raise HTTPException(status_code=400, detail=redact_text(str(e))) from e
    elif transcript_file and transcript_file.filename:
        data = await transcript_file.read()
        try:
            text = extract_text_from_bytes(data, transcript_file.filename)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        if is_insufficient_transcript(text):
            raise HTTPException(
                status_code=400,
                detail="insufficient_content: transcript lacks usable meeting content",
            )
        run.transcript = Transcript(text=text, source="upload")
    elif transcript:
        if is_insufficient_transcript(transcript):
            raise HTTPException(
                status_code=400,
                detail="insufficient_content: transcript lacks usable meeting content",
            )
        run.transcript = Transcript(text=transcript, source="paste")
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide transcript text, transcript file (.txt/.pdf), or audio",
        )

    if account_json:
        run.account = AccountDossier.model_validate_json(account_json)
    elif deal_id:
        try:
            hubspot = hubspot_client_for_user(user.id)
            run.account = await hubspot.get_deal(deal_id)
        except CredentialsMissing as e:
            raise _http_from_creds(e) from e
        except Exception as e:
            raise _http_from_creds(e) from e
    else:
        raise HTTPException(status_code=400, detail="Provide account_json or deal_id")

    # SOW precedence: uploaded file > saved library id > pasted text
    if sow_file and sow_file.filename:
        data = await sow_file.read()
        try:
            text = extract_text_from_bytes(data, sow_file.filename)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        run.scope_corpus = ScopeCorpus(
            source=sow_file.filename or "sow_upload",
            raw_text=text,
            items=[],
        )
    elif sow_id and sow_id.strip():
        sow = get_sow_store().get_for_user(sow_id.strip(), user.id)
        if not sow:
            raise HTTPException(status_code=404, detail="Saved SOW not found")
        run.scope_corpus = ScopeCorpus(
            source=f"saved:{sow.id}",
            raw_text=sow.content,
            items=[],
        )
    elif scope_text and scope_text.strip():
        run.scope_corpus = ScopeCorpus(source="inline", raw_text=scope_text.strip(), items=[])

    try:
        with llm_override(llm_for_user(user.id)):
            run = await process_run(run)
    except CredentialsMissing as e:
        raise _http_from_creds(e) from e
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=redact_text(str(exc))) from exc
    store.save(run)
    return run


@router.get("", response_model=list[RunRecord])
async def list_runs(user: CurrentUser = Depends(get_current_user)):
    return get_run_store().list_runs(user_id=user.id)


@router.get("/{run_id}", response_model=RunRecord)
async def get_run(run_id: str, user: CurrentUser = Depends(get_current_user)):
    run = get_run_store().get_for_user(run_id, user.id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/{run_id}/resume", response_model=RunRecord)
async def resume_run(
    run_id: str,
    approved: ApprovedPayload,
    user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    run = get_run_store().get_for_user(run_id, user.id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != RunStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Run is not awaiting approval")

    if not any(
        [
            approved.sections.emails,
            approved.sections.crm,
            approved.sections.tasks,
        ]
    ):
        raise HTTPException(
            status_code=400,
            detail="Approve at least one section (email, CRM, or tasks) before confirming",
        )

    run.approved = approved
    run.status = RunStatus.APPROVED
    get_run_store().save(run)
    return run


@router.post("/{run_id}/execute", response_model=RunRecord)
async def execute_run(
    run_id: str,
    user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    run = get_run_store().get_for_user(run_id, user.id)
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

    try:
        executor = WorkflowExecutor(
            hubspot=hubspot_client_for_user(user.id),
            gmail=gmail_client_for_user(user.id),
            jira=jira_client_for_user(user.id),
            user_id=user.id,
        )
        await executor.execute(run, approved)
    except CredentialsMissing as e:
        run.status = RunStatus.FAILED
        run.error = str(e)
        get_run_store().save(run)
        raise _http_from_creds(e) from e
    return run


@router.post("/from-sample/{case_id}", response_model=RunRecord)
async def create_from_sample(
    case_id: str,
    user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
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
        try:
            stt = stt_for_user(user.id)
            audio_bytes = (ROOT_DIR / inp["audio"]).read_bytes()
            transcript_obj = await stt.transcribe(audio_bytes, "audio/m4a")
            transcript = transcript_obj.text
        except CredentialsMissing as e:
            raise _http_from_creds(e) from e

    account = None
    if inp.get("account"):
        account = load_account_from_file(ROOT_DIR / inp["account"])
    elif inp.get("deal_id"):
        try:
            hubspot = hubspot_client_for_user(user.id)
            account = await hubspot.get_deal(inp["deal_id"])
        except CredentialsMissing as e:
            raise _http_from_creds(e) from e
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
        user_id=user.id,
        transcript=Transcript(text=transcript, source="upload"),
        account=account,
        scope_corpus=scope,
    )
    try:
        with llm_override(llm_for_user(user.id)):
            run = await process_run(run)
    except CredentialsMissing as e:
        raise _http_from_creds(e) from e
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=redact_text(str(exc))) from exc
    get_run_store().save(run)
    return run
