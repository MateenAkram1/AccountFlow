# Failure Analysis Log

**Requirement:** ≥3 failure cases with root-cause analysis (Day 4)

---

## FAIL-01: Hallucinated deadline on short calls (TC-06)

| Field | Value |
|-------|-------|
| Test case | TC-06 |
| Symptom | Draft engine invented deadlines not spoken on a 2-line call |
| Root cause | Heuristic fallback always emits generic follow-up tasks regardless of transcript length |
| Fix applied | `HallucinationGrader` fails grounding when transcript &lt;15 words and task mentions deadlines not in text |
| Regression | PASS after fix |
| Residual risk | Live LLM may still hallucinate; human approval remains required |

---

## FAIL-02: Owner ambiguity on duplicate first names (TC-05)

| Field | Value |
|-------|-------|
| Test case | TC-05 |
| Symptom | Multiple "Ahmed" speakers caused uncertain task ownership |
| Root cause | Draft engine defaulted owner to AE without confidence penalty |
| Fix applied | Heuristic draft sets confidence &lt;0.7 and owner `TBD — review owners` when name repetition detected |
| Regression | PASS after fix |
| Residual risk | Uncommon names or implicit owners still need manual edit |

---

## FAIL-03: Gmail API transient failure (TC-09)

| Field | Value |
|-------|-------|
| Test case | TC-09 |
| Symptom | Email send fails with 503; user unclear what happened |
| Root cause | No retry/backoff wrapper on first integration pass |
| Fix applied | `GmailClient.send` retries 3× with httpx; mock mode documents fallback path |
| Regression | PASS (retry logic in place; mock eval documents expected behavior) |
| Residual risk | After 3 failures, user must send from saved draft manually |

---

## Additional findings

- **TC-12 garbled input:** `is_insufficient_transcript()` blocks processing before LLM spend.
- **TC-10 partial execute:** `ApprovedSections` flags allow CRM+Jira without email send.
