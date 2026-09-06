# AccountFlow OS — 5-Day Sprint Plan

**Product:** Meeting + account context → scope verify → approve → execute (email, CRM, tasks)  
**User (proxy):** Alex Rivera — AE/PM, 8–12 client calls/week  
**Core question:** Whose workflow changed, what system built, how proved better?

**Time:** 4 days remaining | ~8h/day

---

## Locked scope

| In v1 | Out of v1 (non-goals) |
|-------|------------------------|
| Record/upload → transcribe | Auto-send without approval |
| HubSpot read + write | Salesforce |
| Gmail send | Zoom bot in calls |
| Jira create tasks | Multi-tenant SaaS / billing |
| SOW upload → Scope Verifier | Full CRM two-way sync |
| Approval web UI + Execute | English-only (v1) |

**Primary metric:** Minutes from call end → email sent + CRM updated (target <8 vs 30–40 manual)

**Stack:** Python 3.11, LangGraph, FastAPI, Next.js, SQLite, Deepgram/Whisper, OpenAI gpt-4o-mini

---

## Deliverable map (assessment → file)

| Required | Deliverable | File / location |
|----------|-------------|-----------------|
| Working system | Runnable repo + samples | `app/`, `web/`, `samples/`, `docker-compose.yml` |
| Working system | Example config | `.env.example` |
| Evaluation | 8–12 test cases | `eval/test_cases.json` |
| Evaluation | Baseline + results | `docs/evaluation/BASELINE.md`, `RESULTS.md` |
| Evaluation | Rubric + failures | `docs/evaluation/RUBRIC.md`, `FAILURES.md` |
| Case study | Portfolio narrative | `docs/case-study/CASE_STUDY.md` |
| AI note | Collaboration log | `docs/case-study/AI_COLLABORATION.md` |
| Demo | 5-min video script | `docs/case-study/DEMO_SCRIPT.md` |
| Handoff | Runbook | `docs/RUNBOOK.md` |

---

## Day 1 — Discover, Map, and Baseline

**Key question:** Is the problem real, recurring, and measurable?

### Tasks (~8h)
- [ ] Finalize persona → `docs/workflow/USER.md` (done)
- [ ] Workflow map → `docs/workflow/CURRENT_STATE.md` (done)
- [ ] Document pain: frequency, time, rework
- [ ] Run baseline: manual (3 calls, timed) + naive ChatGPT (3 calls)
- [ ] Create sample fixtures → `samples/` (transcripts, SOW, account JSON)
- [ ] Confirm 12 test cases → `eval/test_cases.json` (done)

### Day 1 outputs (required)
- [x] Target user + job-to-be-done
- [x] Workflow map (trigger → input → judgment → tool → approval → output → exception)
- [ ] Pain evidence + baseline timings → `docs/evaluation/BASELINE.md`
- [x] Success metric + non-goals → `docs/DECISIONS.md`
- [x] 8–12 test cases
- [x] v1 scope locked

---

## Day 2 — Design + Ship v0

**Key question:** Can this become a repeatable system?

### Tasks (~8h)
- [ ] Scaffold `app/` + `docker-compose.yml`
- [ ] Pydantic schemas (AccountDossier, ScopeReport, ActionPackage)
- [ ] LangGraph workflow: ingest → scope_verify → draft → grade
- [ ] Eval rubric finalized → `docs/evaluation/RUBRIC.md`
- [ ] **v0:** CLI one transcript → ActionPackage JSON (happy path)

### Day 2 outputs (required)
- [ ] Architecture → `docs/architecture/SYSTEM.md`
- [ ] Integrations design → `docs/architecture/INTEGRATIONS.md`
- [ ] Schemas, HITL points, fallbacks, privacy
- [ ] Evaluation rubric
- [ ] v0 end-to-end (no UI)

---

## Day 3 — Build Working Core

**Key question:** Can someone else run it without you?

### Tasks (~8h)
- [ ] HubSpot OAuth read + write
- [ ] Gmail OAuth send
- [ ] Jira API create issues
- [ ] FastAPI: runs, approve, execute
- [ ] Next.js Approval Inbox (record/upload, review, execute)
- [ ] Structured logs, validation, error messages
- [ ] `.env.example` + config separated
- [ ] Proxy user test (scripted, no dev help)

### Day 3 outputs (required)
- [ ] E2E: trigger → approved → executed output
- [ ] ≥2 integrations (target: 5)
- [ ] Web UI for non-dev
- [ ] First proxy user run documented in `docs/evaluation/RESULTS.md`

---

## Day 4 — Evaluate, Break, Harden

**Key question:** Can you explain quality across conditions?

### Tasks (~8h)
- [ ] `eval/run_eval.py` — run all 12 cases
- [ ] Fill baseline vs system comparison
- [ ] Document ≥3 failures + root cause → `FAILURES.md`
- [ ] Add retries, confidence UI, fallbacks
- [ ] Re-run regression; update `RESULTS.md`
- [ ] Proxy user feedback + fixes

### Day 4 outputs (required)
- [ ] Full test results + pass/fail
- [ ] Quality, latency, cost, human-touch metrics
- [ ] ≥3 failure analyses
- [ ] Before/after regression

---

## Day 5 — Handoff, Prove Value, Present

**Key question:** Can another person run, trust, and improve it?

### Tasks (~8h)
- [x] Fresh clone test: 3-step setup in README
- [x] Complete `RUNBOOK.md`
- [x] Complete case study + AI collaboration note
- [ ] Record 5-min demo (`DEMO_SCRIPT.md`) — operator records from live URLs + `samples/demo/`
- [x] 2-week adoption plan in case study
- [x] Submission checklist review (`docs/submission/` pack)

### Day 5 outputs (required)
- [x] Runnable repo + sample executable path
- [x] User README + operator runbook
- [x] Architecture, eval, results, limitations documented
- [ ] Demo video (record using `docs/case-study/DEMO_SCRIPT.md`)
- [x] Portfolio case study

---

## Repo structure (implementation)

```
Must Quest/
├── app/
│   ├── api/           # FastAPI, OAuth
│   ├── agents/        # LangGraph
│   ├── integrations/  # hubspot, gmail, jira, stt
│   ├── models/        # Pydantic
│   └── services/      # scope verifier, graders
├── web/               # Next.js Approval Inbox
├── eval/
│   ├── test_cases.json
│   └── run_eval.py
├── samples/           # Anonymized fixtures
├── docs/              # Sprint + eval + case study only
├── docker-compose.yml
├── Makefile
├── .env.example
└── README.md
```

---

## Evaluation rubric weights (how judges score)

| Area | Weight | Our proof |
|------|--------|-----------|
| Problem & scope | 15% | Recurring post-call admin; 7 non-goals; time metric |
| Architecture | 20% | 4-engine design; schemas; HITL; fallbacks |
| Working product | 20% | E2E execute; logs; Docker reproducible |
| Evaluation | 20% | 12 cases; baseline; 3+ failures analyzed |
| Non-dev UX | 15% | Web inbox; runbook; proxy user test |
| Communication | 10% | Case study; demo; honest limitations |

---

## Risk mitigations

| Risk | Mitigation |
|------|------------|
| OAuth delays | Sandbox accounts Day 1 |
| Scope creep | Non-goals enforced |
| Eval without live APIs | Mock mode + sample JSON |

---

## Daily exit check

1. Did I ship today's required outputs?
2. Can a non-dev demo today's work?
3. What failed and what did I learn?
