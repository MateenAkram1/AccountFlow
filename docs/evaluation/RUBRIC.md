# Evaluation Rubric — Pass/Fail Criteria

## Per-test-case scoring

| Grade | Criteria |
|-------|----------|
| **PASS** | All `expected` fields in test_cases.json met; no unhandled errors |
| **PARTIAL** | Core path works; minor field mismatch fixable by human edit |
| **FAIL** | Wrong scope flag, hallucination shipped, execute without approval, or crash |

---

## Dimension rubrics

### 1. Scope Verifier accuracy
| Score | Definition |
|-------|------------|
| Pass | Correct IN_SCOPE / OUT_OF_SCOPE / TIMELINE_DRIFT classification |
| Fail | Missed out-of-scope ask or false positive on clear in-scope item |

### 2. Hallucination grounding
| Score | Definition |
|-------|------------|
| Pass | Every CRM field, task, email claim has evidence quote in transcript |
| Fail | Invented date, person, or commitment not in source |

### 3. Context consistency
| Score | Definition |
|-------|------------|
| Pass | Email references account history; no CRM contradiction unflagged |
| Fail | Wrong company name, stage, or contact |

### 4. Execute reliability
| Score | Definition |
|-------|------------|
| Pass | Approved actions complete; external IDs logged |
| Fail | Silent failure, duplicate send, or execute without approval |

### 5. Human-touch rate
| Score | Definition |
|-------|------------|
| Good | ≤3 field edits per run on happy paths |
| Acceptable | ≤6 edits on edge cases |
| Poor | Full rewrite required |

### 6. Latency (P95)
| Score | Target |
|-------|--------|
| Pass | <90 sec ingest → draft ready |
| Fail | >180 sec without explanation |

### 7. Cost per run
| Track | Log tokens + API calls; report mean/median in RESULTS.md |

---

## Baseline comparison table (fill Day 4)

| Metric | Manual | Naive ChatGPT | AccountFlow OS |
|--------|--------|---------------|----------------|
| Time to email + CRM (min) | | | |
| Scope issues caught | | | |
| CRM fields correct (%) | | | |
| Human edits required | N/A | | |
| Cost per run ($) | $0 | | |

---

## Automated vs manual eval

| Check | Automated (`eval/run_eval.py`) | Manual (human review) |
|-------|-------------------------------|------------------------|
| Schema validation | ✅ | |
| Scope flag presence | ✅ | |
| Hallucination grader | ✅ | Spot-check |
| Email tone/quality | | ✅ |
| UX clarity | | ✅ proxy user test |
