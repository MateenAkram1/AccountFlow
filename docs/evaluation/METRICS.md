# Evaluation Metrics — AccountFlow OS

**Primary metric (locked):** Time from call end → email sent + CRM updated

---

## Primary metric

| Field | Value |
|-------|-------|
| **Name** | Post-call action completion time |
| **Unit** | Minutes |
| **Baseline (manual)** | Target: 30–40 min (fill Day 1) |
| **Baseline (naive ChatGPT)** | Target: 15–25 min + manual tool work (fill Day 1) |
| **Target (Day 5)** | < 8 min |
| **Final result** | _fill Day 4_ |

---

## Secondary metrics

| Metric | Baseline | Target | Final |
|--------|----------|--------|-------|
| Scope issues caught (of planted cases) | ~0% manual miss | 90%+ | |
| CRM fields correct (of 5 key fields) | ~70% | 95%+ with approval | |
| Human field edits per run | N/A | ≤3 happy / ≤6 edge | |
| Execute success rate | N/A | >95% | |
| Hallucination catch rate (TC-06) | 0% ChatGPT | 100% blocked | |
| P95 latency (upload → draft ready) | N/A | <90 sec | |
| Cost per run (USD) | $0 manual | track | |

---

## Quality dimensions (rubric summary)

1. **Scope Verifier** — correct IN/OUT scope classification
2. **Grounding** — evidence quote per claim
3. **Context** — email uses HubSpot history
4. **Execute** — approved actions complete with logged IDs
5. **UX** — non-dev completes flow without help

See `docs/evaluation/RUBRIC.md`.

---

## Human-touch metric

**Human intervention rate** = (runs requiring edit before execute) / (total runs)

Track separately for happy vs edge cases. Goal: demonstrate AI handles draft, human handles judgment.

---

## Cost tracking

Log per run:
- LLM tokens (input/output)
- STT minutes
- API calls (HubSpot, Gmail, Jira)

Report mean/median in `docs/evaluation/RESULTS.md`.

---

## Adoption metrics (2-week plan — case study)

| Week | Metric | Target |
|------|--------|--------|
| 1 | Runs by proxy user | 5 |
| 1 | Avg completion time | <10 min |
| 2 | Execute success rate | >95% |
| 2 | Scope flag precision | >85% |
