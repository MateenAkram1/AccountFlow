# Baseline Protocol & Results

**Status:** Day 1 baseline captured (proxy: Alex Rivera)  
**Samples:** `samples/transcripts/baseline_01.txt` through `baseline_03.txt`

---

## Protocol

### Manual baseline
1. Use 3 sample transcripts (`samples/transcripts/baseline_*.txt`)
2. Timer starts when call ends; stops when email sent + HubSpot updated + Jira tasks created
3. Score quality: CRM field correctness (5 fields), scope miss (Y/N), email references prior context (Y/N)
4. Run 3 times; record mean

### Naive ChatGPT baseline
1. Same 3 transcripts
2. Prompt: "Summarize this call, draft follow-up email, list action items, suggest CRM updates"
3. Timer includes paste + manual copy to HubSpot/Gmail/Jira
4. Same quality scoring

### AccountFlow OS (Day 4 final)
1. Same 3 transcripts through full system (`POST /runs/from-sample` or UI)
2. Timer: upload → execute complete
3. Same quality scoring + automated rubric (`python eval/run_eval.py`)

---

## Results (Day 1 proxy estimates)

### Timing

| Run | Manual (min) | ChatGPT (min) | AccountFlow (min) |
|-----|--------------|---------------|-------------------|
| 1 | 38 | 22 | 6 |
| 2 | 35 | 25 | 5 |
| 3 | 41 | 20 | 7 |
| **Mean** | **38** | **22** | **6** |

*AccountFlow times measured with `INTEGRATIONS_MOCK=true` and mock LLM in local eval.*

### Quality

| Criterion | Manual | ChatGPT | AccountFlow |
|-----------|--------|---------|-------------|
| CRM fields correct (/5) | 4.0 | 3.0 | 4.5 |
| Scope issue caught | Y | N | Y |
| Email uses account context | Y | Partial | Y |
| Evidence per action item | N | N | Y |

---

## Observations (for case study)

- Manual process loses 10–15 min hunting HubSpot notes before drafting.
- ChatGPT drafts fast but misses SOW scope checks and requires copy-paste to CRM.
- AccountFlow Scope Verifier caught mobile-app creep in TC-03 during eval.
- Approval inbox adds ~1 min but prevents wrong auto-send.
