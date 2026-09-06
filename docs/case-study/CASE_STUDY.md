# Case Study — AccountFlow OS

**Status:** Day 5 complete  
**Live web:** https://accountflow-web.vercel.app  
**Live API:** https://accountflow-api.vercel.app  

---

## 1. User & problem

**Who:** Alex Rivera, AE / client-delivery PM at a distributed B2B services firm.  
**Problem:** After every client call she spends 30–40 minutes writing follow-ups, updating HubSpot, and filing Jira tasks — and still misses out-of-scope asks buried in the conversation.  
**Frequency:** 8–12 calls/week (about 4–8 hours/week of post-call admin).  
**Business value:** Cut post-call cycle time under 8 minutes while catching scope creep before it becomes unpaid work.

---

## 2. Existing workflow & bottleneck

See `docs/workflow/CURRENT_STATE.md`.

Typical path today:

1. Scramble for HubSpot notes and SOW PDF  
2. Draft email from memory  
3. Hand-edit CRM fields  
4. Create Jira tickets one by one  

**Bottleneck:** Manual glue between meeting memory, contract (SOW), HubSpot, Gmail, and Jira — with no verification layer. ChatGPT speeds drafting but still requires copy-paste and does not check the SOW.

---

## 3. Scope decisions & non-goals

**In scope (v1):** Upload or record transcript → attach HubSpot deal → attach SOW → Scope Verifier → human approve → execute Gmail / HubSpot / Jira.  

**Out of scope (locked):**

1. Auto-send without approval  
2. Zoom/Meet bot that joins calls  
3. Salesforce  
4. Multi-tenant billing / org SaaS layer (open register + per-user BYOK instead)  
5. Non-English transcripts  

See `docs/DECISIONS.md`.

---

## 4. Architecture & major trade-offs

See `docs/architecture/SYSTEM.md`.

| Choice | Why |
|--------|-----|
| Transcript-in (not meeting bot) | Privacy + 5-day feasibility |
| LangGraph + interrupt for approval | Explicit human gate before execute |
| FastAPI + Next.js | Clear API/UI split; deploy independently |
| BYOK vault (Fernet) | Operator does not hold shared HubSpot/Jira/LLM secrets |
| Turso in production | Local SQLite on Vercel wiped between cold starts |
| HubSpot pipeline stages via API | Stop guessing stage IDs in the approval UI |

**Key trade-off:** We spend ~1 minute on approval to prevent wrong emails and CRM writes. That is intentional, not a bug.

---

## 5. Work delegated to AI vs judgment retained by humans

| AI | Human |
|----|-------|
| Transcribe (STT), extract actions, draft email/CRM/tasks | Approve or reject every section |
| Scope flags (IN/OUT/TIMELINE/BUDGET) | Override flags; choose change_request vs follow-up |
| Hallucination grader on weak transcripts | Edit low-confidence owners and values |
| Propose HubSpot stage / amount | Confirm against real pipeline dropdowns |

---

## 6. Results

Measured sources only: `docs/evaluation/BASELINE.md`, `docs/evaluation/RESULTS.md`.

| Metric | Before (manual) | After (AccountFlow) |
|--------|-----------------|---------------------|
| Time to email + CRM (mean) | **38 min** | **6 min** (mock path) |
| Scope issues caught (baseline sample) | Y (if careful) / ChatGPT **N** | **Y** |
| CRM fields correct (/5) | 4.0 | **4.5** |
| Automated suite | — | **12/12 PASS** |

Primary target was &lt;8 minutes — **met** on the timed mock path. Live LLM + real APIs will be slower; that must be re-measured in week 1 of adoption.

---

## 7. Failures, changes, limitations

**Failures fixed (see `docs/evaluation/FAILURES.md`):**

- Short calls inventing deadlines (TC-06) → grader + approval  
- Duplicate first names (TC-05) → low confidence / TBD owner  
- Gmail 503 (TC-09) → three retries, then clear error  

**Other product corrections during the sprint:**

- Session bounce on Vercel cold starts → restore user from JWT; Turso for durable data  
- Cross-site cookies → `SameSite=None` + `Secure` in production  
- HubSpot CRM fields as free text → pipeline stage dropdowns; multi-deal create/select  

**Limitations (honest):**

- English-only v1  
- Scope Verifier quality tracks SOW quality  
- Owner assignment still needs human review when names collide  
- Per-call $ cost and production P95 latency were **not instrumented**  
- Demo/eval often uses mock LLM/integrations; live keys change latency and failure modes  

---

## 8. Two-week iteration plan

### Week 1

- Proxy user runs **5** anonymized real calls on the live URLs  
- Track: wall-clock time, edit count, execute success  
- Tune Scope Verifier false positives against real SOWs  
- Add simple per-run token/API cost logging  

### Week 2

- Optional Zoom/Meet recording ingest **or** Slack notify on execute  
- Commitment tracker across runs for the same deal  
- HubSpot production OAuth review with security  

### Near-term backlog

- Instrument P95 draft latency in production  
- Calendar-aware owner resolution  
- Stronger SOW parsing (structured sections, not only raw text)  
- Optional always-on API host if Vercel cold starts become painful for demos  

---

## 9. Adoption metrics (planned post-deployment)

| Metric | Week 1 target | Week 2 target |
|--------|---------------|---------------|
| Runs completed | 5 | 10 |
| Avg time per run (live) | &lt;10 min | &lt;8 min |
| Execute success rate | &gt;90% | &gt;95% |
| Scope flag precision | measure | &gt;85% |
