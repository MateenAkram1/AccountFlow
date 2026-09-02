import pytest

from accountflow.agents.graph import build_graph, process_run
from accountflow.models.schemas import AccountDossier, Contact, RunRecord, RunStatus, Transcript


@pytest.mark.asyncio
async def test_process_run_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    from accountflow.providers.registry import clear_provider_cache

    clear_provider_cache()
    run = RunRecord(
        transcript=Transcript(
            text="Let's finalize the API spec and send documentation by Friday.",
            source="paste",
        ),
        account=AccountDossier(
            deal_id="demo-001",
            company="Acme Corp",
            stage="discovery",
            contacts=[Contact(name="Sarah", role="CTO", email="sarah@acme.example")],
        ),
    )
    result = await process_run(run)
    assert result.status == RunStatus.AWAITING_APPROVAL
    assert result.action_package is not None
    assert result.grade_report is not None


def test_build_graph_compiles():
    graph = build_graph()
    assert graph is not None
