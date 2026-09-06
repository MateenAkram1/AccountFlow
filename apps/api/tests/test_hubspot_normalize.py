import pytest

from accountflow.integrations.hubspot import (
    HubSpotClient,
    _mock_pipelines,
    _normalize_hubspot_properties,
)
from accountflow.models.schemas import CRMUpdate


def test_maps_proposal_stage_to_hubspot_id():
    props = _normalize_hubspot_properties(
        [CRMUpdate(field="dealstage", value="proposal", evidence_quote="x", confidence=0.9)]
    )
    assert props["dealstage"] == "presentationscheduled"


def test_maps_discovery_stage():
    props = _normalize_hubspot_properties(
        [CRMUpdate(field="stage", value="discovery", evidence_quote="x", confidence=0.9)]
    )
    assert props["dealstage"] == "appointmentscheduled"


def test_passes_through_custom_hubspot_stage_id():
    props = _normalize_hubspot_properties(
        [
            CRMUpdate(
                field="dealstage",
                value="customstage123",
                evidence_quote="x",
                confidence=0.9,
            )
        ]
    )
    assert props["dealstage"] == "customstage123"


def test_ignores_unknown_crm_fields():
    props = _normalize_hubspot_properties(
        [
            CRMUpdate(field="budget_signal", value="50k", evidence_quote="x", confidence=0.9),
            CRMUpdate(field="amount", value="$40,000", evidence_quote="x", confidence=0.9),
        ]
    )
    assert "budget_signal" not in props
    assert props["amount"] == "40000"


def test_mock_pipelines_have_default_stages():
    pipes = _mock_pipelines()
    assert pipes[0]["id"] == "default"
    ids = {s["id"] for s in pipes[0]["stages"]}
    assert "presentationscheduled" in ids
    assert "closedwon" in ids


@pytest.mark.asyncio
async def test_create_deal_mock(auth_env, monkeypatch):
    monkeypatch.setenv("INTEGRATIONS_MOCK", "true")
    from accountflow.core.config import clear_settings_cache

    clear_settings_cache()
    client = HubSpotClient(access_token="unused", allow_env_fallback=False)
    deal = await client.create_deal(
        name="Meridian CareOps",
        amount="120000",
        stage_id="qualifiedtobuy",
        pipeline_id="default",
    )
    assert deal["created"] is True
    assert deal["name"] == "Meridian CareOps"
    assert deal["stage"] == "qualifiedtobuy"
    assert deal["amount"] == "120000"


@pytest.mark.asyncio
async def test_list_pipelines_mock(auth_env, monkeypatch):
    monkeypatch.setenv("INTEGRATIONS_MOCK", "true")
    from accountflow.core.config import clear_settings_cache

    clear_settings_cache()
    client = HubSpotClient(access_token="unused", allow_env_fallback=False)
    pipes = await client.list_pipelines()
    assert len(pipes) >= 1
    assert pipes[0]["stages"]
