# Case Study — AccountFlow OS

**Status:** Template — complete Day 5  
**Portfolio-ready:** Yes

---

## 1. User & problem

**Who:** Alex Rivera, AE/Client Delivery PM at distributed B2B services firm.  
**Problem:** 30–40 minutes after every client call spent on email, CRM, Jira — with frequent scope misses and stale deal data.  
**Frequency:** 8–12 calls/week (4–8 hours/week admin).

---

## 2. Existing workflow & bottleneck

_See `docs/workflow/CURRENT_STATE.md`_

**Bottleneck:** Manual glue work between meeting memory, SOW, HubSpot, Gmail, and Jira — no verification layer.

---

## 3. Scope decisions & non-goals

**In scope (v1):** Record/upload → HubSpot context → Scope Verifier → approve → execute Gmail/HubSpot/Jira.  
**Out of scope:** Auto-send, Zoom bot, Salesforce, multi-tenant SaaS.

_See `docs/DECISIONS.md`_

---

## 4. Architecture & trade-offs

_See `docs/architecture/SYSTEM.md`_

**Key trade-off:** Transcript-in vs meeting bot — chose privacy and 5-day feasibility over auto-join.

---

## 5. AI vs human judgment

| AI | Human |
|----|-------|
| Transcribe, extract, draft, scope flag | Approve every execute action |
| Grade hallucinations | Override scope flags |
| Propose workflows | Choose which to run |

---

## 6. Results

| Metric | Before | After |
|--------|--------|-------|
| Time to email + CRM (mean) | _fill_ | _fill_ |
| Scope issues caught | _fill_ | _fill_ |
| Test suite pass rate | — | _fill_ |

_See `docs/evaluation/RESULTS.md`_

---

## 7. Failures, changes, limitations

**Failures:** _See `docs/evaluation/FAILURES.md`_

**Limitations (honest):**
- English-only v1
- Owner assignment ~70–80% without calendar integration
- HubSpot sandbox required for demo
- Scope Verifier depends on SOW quality

---

## 8. Two-week iteration plan

### Week 1
- Proxy user runs 5 anonymized real calls
- Track: time saved, edit count, execute success rate
- Tune Scope Verifier false positive rate

### Week 2
- Add Zoom recording ingest OR Slack execution notify
- Add commitment tracker across runs
- HubSpot production OAuth review

**Backlog:** `docs/BACKLOG.md`

---

## 9. Adoption metrics (planned post-deployment)

| Metric | Week 1 target | Week 2 target |
|--------|---------------|---------------|
| Runs completed | 5 | 10 |
| Avg time per run | <10 min | <8 min |
| Execute success rate | >90% | >95% |
| Scope flag precision | measure | >85% |
