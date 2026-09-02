# Integrations Architecture

**Principle:** Ingest and deliver through **OAuth-connected APIs**. Copy-paste is fallback only for demos without credentials.

---

## Connection model

```
User connects accounts once (OAuth):
  ├── HubSpot (read + write)
  ├── Gmail (send + optional read)
  ├── Jira (read scope + create issues)
  └── Zoom (optional — recording ingest)

Secrets stored in .env / encrypted config — never in repo.
```

---

## Ingestion flows

### 1. Meeting audio → transcript

```
[Record in browser] OR [Upload file] OR [Zoom webhook]
        ↓
   Object storage / temp file
        ↓
   Deepgram or Whisper API
        ↓
   Transcript + speaker segments (if available)
        ↓
   Stored in run record (SQLite)
```

### 2. Account context (HubSpot read)

```
User selects deal ID (search in UI)
        ↓
GET /crm/v3/objects/deals/{id}
GET /crm/v3/objects/deals/{id}/associations/contacts
GET /crm/v3/objects/deals/{id}/associations/notes
        ↓
AccountDossier JSON → Intelligence engine
```

**Fields pulled:** company, stage, amount, close date, last activity, contact names/emails, recent notes.

### 3. Scope document (SOW)

```
User uploads PDF/DOCX OR links Jira epic
        ↓
Extract text (pypdf / docx)
        ↓
Chunk + index OR structured parse
        ↓
ScopeCorpus → Scope Verifier
```

**Alternative:** Jira API `GET /issue/{epicKey}` + child issues = live scope.

---

## Scope Verifier (detailed)

### Inputs
- `transcript` — full meeting text
- `scope_corpus` — SOW text or Jira epic + stories
- `account_dossier` — deal value, timeline from CRM

### Process
1. **Extract requests** from transcript ("Can you add X", "We need Y by date Z")
2. **Match** each request against scope corpus (semantic + keyword)
3. **Classify:**
   - `IN_SCOPE` — matches SOW line
   - `OUT_OF_SCOPE` — not in SOW
   - `TIMELINE_DRIFT` — date conflict
   - `BUDGET_SIGNAL` — money/approval mentioned vs contract cap
   - `AMBIGUOUS` — needs human judgment
4. **Output** `ScopeReport` with flags + evidence + recommended workflow

### Example output

```json
{
  "flags": [
    {
      "type": "OUT_OF_SCOPE",
      "request": "Mobile offline mode",
      "evidence_quote": "Can you make it work offline?",
      "sow_reference": null,
      "severity": "high",
      "recommended_workflow": "change_request"
    },
    {
      "type": "IN_SCOPE",
      "request": "API integration",
      "evidence_quote": "Let's finalize the API spec",
      "sow_reference": "Section 3.2 — REST API delivery",
      "severity": "none"
    }
  ]
}
```

---

## Execution flows

### Send email (Gmail)

```
Approved EmailDraft
        ↓
POST gmail.users.messages.send
  - to, subject, body (HTML)
  - threadId (optional — reply in thread)
        ↓
Log messageId in run audit
```

### Update CRM (HubSpot)

```
Approved CRMUpdate[]
        ↓
PATCH /crm/v3/objects/deals/{id}
  - properties: { dealstage, notes, hs_next_step, ... }
        ↓
POST /crm/v3/objects/notes  (call log)
  - body: meeting summary + link to run
        ↓
Log HubSpot response IDs
```

### Create tasks (Jira)

```
Approved Task[]
        ↓
POST /rest/api/3/issue (per task)
  - project, summary, description, due date
  - link to deal/account in description
        ↓
Log Jira issue keys
```

### Start workflow

```
User clicks "Run: Client Follow-up"
        ↓
LangGraph workflow:
  1. send_email (Gmail) — if approved
  2. update_crm (HubSpot) — if approved
  3. create_tasks (Jira) — if approved
  4. interrupt if any step fails → show error in UI
        ↓
WorkflowRun log with per-step status
```

---

## Error handling

| Failure | Behavior |
|---------|----------|
| HubSpot rate limit | Retry 3x with backoff |
| Gmail auth expired | Prompt re-connect OAuth |
| Jira project not found | Block execute, show fix |
| Scope doc unreadable | Warn, run without scope verifier |
| Transcribe failed | Retry or ask for text upload |

All errors logged with `run_id` for Day 4 failure analysis.

---

## v1 integration checklist (Day 3 deliverable)

- [ ] HubSpot OAuth app created (read deal + write deal + create note)
- [ ] Gmail OAuth app created (send scope)
- [ ] Jira API token or OAuth (create issue)
- [ ] `.env.example` with all required keys documented
- [ ] `config/integrations.yaml` — enabled connectors per deployment
- [ ] One-command setup: `docker compose up` + connect accounts in UI
