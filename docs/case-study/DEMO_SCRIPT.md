# Demo Video Script (5 minutes)

**Requirement:** Problem, baseline, live flow, non-dev UX, evaluation, key limitation

---

## [0:00–0:45] Problem & baseline (45 sec)

**Say:**
> "Alex runs 10 client calls a week. After each one, she spends 35 minutes updating HubSpot, writing follow-up emails, and creating Jira tasks — and still misses out-of-scope requests. We timed it: 38 minutes manual, 22 with ChatGPT but still copy-paste to tools."

**Show:** Baseline table from `BASELINE.md`

---

## [0:45–1:15] What we built (30 sec)

**Say:**
> "AccountFlow OS connects meeting capture, HubSpot account context, and the SOW contract. It verifies scope, drafts actions, and after Alex approves — sends email, updates CRM, and creates Jira tickets via API."

**Show:** Architecture diagram (4 engines)

---

## [1:15–3:30] Live flow — non-dev UX (2 min 15 sec)

1. Select HubSpot deal (integration pull)
2. Upload sample transcript OR show recording
3. Scope Verifier flag: **OUT OF SCOPE — mobile app**
4. Approval Inbox: edit email line, approve CRM + tasks
5. Click **Execute** → show Gmail sent, HubSpot updated, Jira keys
6. Show audit log with evidence quotes

**Emphasize:** "Nothing executed without approval."

---

## [3:30–4:15] Evaluation (45 sec)

**Show:**
- 12 test cases, pass rate
- One failure we caught: hallucinated deadline (TC-06)
- Metrics: 38 min → 7 min mean; scope caught 3/3 on test set

---

## [4:15–5:00] Limitation & next steps (45 sec)

**Say:**
> "Limitation: owner assignment drops to 70% when two people share a name — we force human review below 0.7 confidence. Next two weeks: Zoom ingest and commitment tracking across calls."

**Show:** 2-week plan from case study

---

## Recording checklist

- [ ] `make install` or `docker compose up --build`
- [ ] `LLM_PROVIDER=mock` for offline demo, or live Gemini key
- [ ] Sample data only (no real client PII)
- [ ] Demo path: New Run → paste `samples/transcripts/tc03_scope_creep.txt` → Approve → Execute
- [ ] Show run_id in UI
- [ ] 5:00 or under
