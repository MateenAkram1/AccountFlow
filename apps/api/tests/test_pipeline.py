import pytest

from accountflow.providers.mock import MockLLMProvider, MockSTTProvider
from accountflow.providers.registry import clear_provider_cache, get_llm, get_stt
from accountflow.services.pipeline import (
    DraftEngine,
    HallucinationGrader,
    ScopeVerifier,
)
from accountflow.models.schemas import (
    AccountDossier,
    ActionPackage,
    Contact,
    ScopeCorpus,
    ScopeItem,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_provider_cache()
    yield
    clear_provider_cache()


def test_mock_llm_provider():
    import os
    os.environ["LLM_PROVIDER"] = "mock"
    clear_provider_cache()
    llm = get_llm("mock")
    assert llm.name == "mock"


def test_mock_stt_provider():
    import asyncio

    async def _run():
        stt = get_stt("mock")
        return await stt.transcribe(b"fake-audio")

    result = asyncio.run(_run())
    assert result.text


@pytest.mark.asyncio
async def test_scope_verifier_heuristic():
    import os
    os.environ["LLM_PROVIDER"] = "mock"
    clear_provider_cache()

    scope = ScopeCorpus(
        source="test",
        raw_text="Web application only. API integration included. Timeline: March 2026.",
        items=[ScopeItem(id="1", description="Web app delivery", section="1")],
        timeline="March 2026",
        budget_cap=40000,
    )
    transcript = "Can you also build a mobile app with offline mode for our team?"
    verifier = ScopeVerifier()
    report = await verifier.verify(transcript, scope)
    assert not report.skipped
    assert any(f.type.value == "OUT_OF_SCOPE" for f in report.flags)


@pytest.mark.asyncio
async def test_draft_engine_heuristic():
    import os
    os.environ["LLM_PROVIDER"] = "mock"
    clear_provider_cache()

    account = AccountDossier(
        deal_id="demo-001",
        company="Acme Corp",
        stage="discovery",
        contacts=[Contact(name="Sarah", role="CTO", email="sarah@acme.example")],
    )
    transcript = "Let's finalize the API spec and send a proposal by Friday."
    drafter = DraftEngine()
    package = await drafter.draft(transcript, account, None)
    assert package.summary
    assert len(package.emails) >= 1
    assert len(package.tasks) >= 1


def test_hallucination_grader():
    account = AccountDossier(deal_id="1", company="Acme", stage="discovery")
    transcript = "Send the proposal by Friday for API integration."
    package = ActionPackage(
        summary="test",
        tasks=[],
        crm_updates=[],
    )
    from accountflow.models.schemas import TaskItem
    package.tasks = [
        TaskItem(
            summary="Send proposal",
            description="Send proposal",
            evidence_quote="Send the proposal by Friday",
            confidence=0.9,
        )
    ]
    grader = HallucinationGrader()
    results = grader.grade(transcript, package)
    assert any(r["passed"] for r in results)
