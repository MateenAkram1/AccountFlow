# System Architecture — AccountFlow OS

**Version:** v1 (assessment)  
**Pattern:** 4-engine pipeline with LangGraph orchestration

---

## High-level architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        WEB — Approval Inbox (Next.js)              │
│  Record | Select Deal | Review | Approve | Execute               │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST
┌────────────────────────────▼────────────────────────────────────┐
│                     API — FastAPI                                │
│  OAuth │ Runs │ Execute │ Webhooks                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│              AGENT — LangGraph Workflow                          │
│  ingest → transcribe → load_context → scope_verify → draft      │
│  → grade → INTERRUPT(approve) → execute_workflow                │
└──────┬──────────────────┬──────────────────┬──────────────────┘
       │                  │                  │
┌──────▼──────┐   ┌───────▼───────┐   ┌──────▼──────┐
│ Integrations│   │   Services    │   │  SQLite DB  │
│ HubSpot     │   │ ScopeVerifier │   │ runs        │
│ Gmail       │   │ Graders       │   │ audit       │
│ Jira        │   │ Workflows     │   │ checkpointer│
│ STT         │   │               │   │             │
└─────────────┘   └───────────────┘   └─────────────┘
```

---

## Boundary definitions

| Layer | Responsibility | Does NOT |
|-------|----------------|----------|
| **Workflow** | Orchestration, state, HITL gates | Call LLM directly |
| **Data** | Pydantic schemas, SQLite persistence | Business logic |
| **Tools** | External API clients (HubSpot, etc.) | UI concerns |
| **Models** | LLM calls, structured output parsing | OAuth |
| **Interface** | Next.js Approval Inbox | Agent logic |

---

## LangGraph workflow nodes

| Node | Input | Output | Notes |
|------|-------|--------|-------|
| `ingest` | audio/file/transcript | `raw_input` | Validate format |
| `transcribe` | audio | `transcript` | Skip if text provided |
| `load_context` | deal_id | `account_dossier` | HubSpot API |
| `load_scope` | sow_file/epic | `scope_corpus` | PDF parse |
| `scope_verify` | transcript + scope | `scope_report` | Flags + workflows |
| `extract` | transcript + dossier | `extractions` | Decisions, asks |
| `draft` | all above | `action_package` | email, crm, tasks |
| `grade` | action_package | `grade_report` | Hallucination, conflict |
| `interrupt_approve` | action_package | human edits | LangGraph interrupt |
| `execute` | approved package | `execution_log` | Gmail, HubSpot, Jira |

---

## Human-in-the-loop (LangGraph `interrupt`)

Execution **cannot** proceed until `interrupt_approve` receives human response:

- `approved_sections: { email, crm, tasks, workflow }`
- `edits: { ... }` per field
- `rejected: [...]`

Checkpointer persists state across interrupt/resume.

---

## Data contracts (key schemas)

| Schema | Fields (summary) |
|--------|------------------|
| `AccountDossier` | deal_id, company, stage, amount, contacts[], notes[] |
| `ScopeCorpus` | items[], timeline, budget_cap, source_doc |
| `ScopeReport` | flags[], severity, recommended_workflow |
| `ActionPackage` | emails[], crm_updates[], tasks[], scope_report |
| `ExecutionLog` | per-action status, external_ids, errors |
| `RunRecord` | run_id, timestamps, metrics, audit trail |

Full schemas in `docs/architecture/schemas/` (Day 2).

---

## Workflow templates

### Client Follow-up
1. Send external email (Gmail)
2. Update HubSpot deal + log call note
3. Create Jira tasks

### Change Request (Scope Verifier trigger)
1. Create Jira CR ticket
2. Draft CR email (approve sub-interrupt)
3. Update HubSpot risk flag
4. (Stretch) Slack notify PM

---

## Fallbacks

| Failure | Fallback |
|---------|----------|
| HubSpot unavailable | Manual account form (pre-filled sample) |
| Gmail auth expired | Show reconnect + save draft locally |
| Jira create fails | Retry 3×; export task CSV |
| SOW missing | Skip scope verify; warn in UI |
| Transcribe fails | Prompt text paste upload |
| Low confidence field | Force human edit before execute |

---

## Trade-offs (document in case study)

| Decision | Chose | Over | Why |
|----------|-------|------|-----|
| CRM | HubSpot | Salesforce | Faster OAuth dev sandbox |
| Orchestration | LangGraph | Raw prompts | HITL + persistence required |
| Storage | SQLite | Postgres | Zero-infra reproducibility |
| Meeting capture | Record/upload | Zoom bot | Privacy, 5-day scope |
| LLM | gpt-4o-mini | gpt-4o | Cost per eval run |

---

## Observability

- Every run: `run_id` (UUID) in all logs
- Structured JSON logs: `timestamp, run_id, node, event, duration_ms`
- Token/cost tracking per run in `RunRecord`
- Execution audit: proposed vs approved vs executed diff

---

## Security

- OAuth tokens encrypted at rest (env + optional local vault)
- Minimum scopes documented in RUNBOOK
- Recording consent UI before capture
- No PII in eval samples committed to repo
