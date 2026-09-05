from accountflow.integrations.hubspot import _normalize_hubspot_properties
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


def test_ignores_unknown_crm_fields():
    props = _normalize_hubspot_properties(
        [
            CRMUpdate(field="budget_signal", value="50k", evidence_quote="x", confidence=0.9),
            CRMUpdate(field="amount", value="$40,000", evidence_quote="x", confidence=0.9),
        ]
    )
    assert "budget_signal" not in props
    assert props["amount"] == "40000"
