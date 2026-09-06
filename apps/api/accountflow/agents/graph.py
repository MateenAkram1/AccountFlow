from typing import Any, TypedDict

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from accountflow.core.config import data_dir
from accountflow.db.store import get_run_store
from accountflow.models.schemas import (
    ActionPackage,
    ApprovedPayload,
    GradeReport,
    GradeResult,
    RunRecord,
    RunStatus,
    Transcript,
)
from accountflow.services.pipeline import DraftEngine, HallucinationGrader, ScopeVerifier, is_insufficient_transcript


class GraphState(TypedDict, total=False):
    run_id: str
    transcript_text: str
    account_json: str
    scope_json: str
    action_package: dict[str, Any]
    grade_report: dict[str, Any]
    approved: dict[str, Any]


async def node_scope_and_draft(state: GraphState) -> GraphState:
    from accountflow.models.schemas import AccountDossier, ScopeCorpus

    account = AccountDossier.model_validate_json(state["account_json"])
    scope = ScopeCorpus.model_validate_json(state["scope_json"]) if state.get("scope_json") else None
    verifier = ScopeVerifier()
    drafter = DraftEngine()
    scope_report = await verifier.verify(state["transcript_text"], scope)
    package = await drafter.draft(state["transcript_text"], account, scope_report)
    return {"action_package": package.model_dump()}


def node_grade(state: GraphState) -> GraphState:
    package = ActionPackage.model_validate(state["action_package"])
    grader = HallucinationGrader()
    results = grader.grade(state["transcript_text"], package)
    report = GradeReport(
        results=[GradeResult.model_validate(r) for r in results],
    )
    return {"grade_report": report.model_dump()}


def node_approve(state: GraphState) -> GraphState:
    payload = interrupt(
        {
            "action": "approve",
            "action_package": state.get("action_package"),
            "grade_report": state.get("grade_report"),
        }
    )
    return {"approved": payload}


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("scope_and_draft", node_scope_and_draft)
    graph.add_node("grade", node_grade)
    graph.add_node("approve", node_approve)
    graph.set_entry_point("scope_and_draft")
    graph.add_edge("scope_and_draft", "grade")
    graph.add_edge("grade", "approve")
    graph.add_edge("approve", END)

    db_path = data_dir() / "checkpoints.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return graph.compile(checkpointer=checkpointer)


def _is_insufficient_transcript(text: str) -> bool:
    return is_insufficient_transcript(text)


async def process_run(run: RunRecord) -> RunRecord:
    if not run.transcript or not run.account:
        run.status = RunStatus.FAILED
        run.error = "Transcript and account are required"
        return run

    if _is_insufficient_transcript(run.transcript.text):
        run.status = RunStatus.FAILED
        run.error = "insufficient_content: transcript lacks usable meeting content"
        return run

    run.status = RunStatus.PROCESSING
    get_run_store().save(run)

    verifier = ScopeVerifier()
    drafter = DraftEngine()
    grader = HallucinationGrader()

    scope_report = await verifier.verify(
        run.transcript.text,
        run.scope_corpus,
    )
    package = await drafter.draft(
        run.transcript.text,
        run.account,
        scope_report,
    )
    results = grader.grade(run.transcript.text, package)
    run.action_package = package
    run.grade_report = GradeReport(
        results=[GradeResult.model_validate(r) for r in results],
    )
    run.status = RunStatus.AWAITING_APPROVAL
    get_run_store().save(run)
    return run
