# Evaluation Metrics — AccountFlow OS

**Primary metric (locked):** Time from call end → email sent + CRM updated

---

## Primary metric

| Field | Value |
|-------|-------|
| **Name** | Post-call action completion time |
| **Unit** | Minutes |
| **Baseline (manual)** | **38** min mean (Day 1 proxy, 3 runs) |
| **Baseline (naive ChatGPT)** | **22** min mean + manual paste into tools |
| **Target (Day 5)** | &lt; 8 min |
| **Final result** | **6** min mean (mock LLM + mock integrations) |

Source: `docs/evaluation/BASELINE.md`.

---

## Secondary metrics

| Metric | Baseline | Target | Final |
|--------|----------|--------|-------|
| Scope issues caught (planted cases) | ChatGPT missed SOW creep | 90%+ | **Caught** on TC-03 / TC-04 / TC-11 in suite |
| CRM fields correct (of 5 key fields) | Manual 4.0/5; ChatGPT 3.0/5 | 95%+ with approval | **4.5/5** on baseline sample |
| Human field edits per run | N/A | ≤3 happy / ≤6 edge | Not counted run-by-run in v1; approval always required |
| Execute success rate (mock suite) | N/A | &gt;95% | **12/12 (100%)** automated suite |
| Hallucination catch (TC-06) | 0% ChatGPT | Blocked | **PASS** (grader flags) |
| P95 latency (upload → draft ready) | N/A | &lt;90 sec | **Not instrumented in v1** |
| Cost per run (USD) | $0 manual labor time | track | **Not instrumented in v1** |

---

## Quality dimensions (rubric summary)

1. **Scope Verifier** — correct IN/OUT/TIMELINE classification  
2. **Grounding** — evidence quote per claim  
3. **Context** — email uses HubSpot history when deal attached  
4. **Execute** — approved actions complete with logged IDs (mock or live)  
5. **UX** — non-dev completes New Run → Approve → Execute  

See `docs/evaluation/RUBRIC.md`.

---

## Human-touch metric

**Human intervention rate** = runs that require approve/edit before execute / total runs  

In v1 this is **100% by design** (no auto-send). Goal of the product is not zero touch — it is AI drafts + human judgment. Baseline observed ~1 minute of approval overhead inside the 6-minute AccountFlow path.

---

## Cost tracking

Not wired in v1. Planned for the two-week iteration:

- LLM tokens (input/output)  
- STT minutes  
- HubSpot / Gmail / Jira API calls  

Until then, RESULTS must not invent dollar figures.

---

## Adoption metrics (2-week plan — case study)

| Week | Metric | Target |
|------|--------|--------|
| 1 | Runs by proxy user | 5 |
| 1 | Avg completion time (live keys) | &lt;10 min |
| 2 | Execute success rate | &gt;95% |
| 2 | Scope flag precision | &gt;85% |
