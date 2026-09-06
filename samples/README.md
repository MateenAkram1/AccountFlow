# Samples — AccountFlow OS fixtures

Synthetic data for eval, baseline, and CLI demos. **No real client data.**

## Demo recording (`demo/`)

Preferred path for the Day 5 demo video (long, realistic fixtures):

| File | Purpose |
|------|---------|
| `demo_meeting_transcript.txt` | Full post-call transcript for New Run paste |
| `demo_sow.txt` | Matching SOW for Scope Verifier |

Short creep demo alternative: `transcripts/tc03_scope_creep.txt` + `sow/acme_web_app.txt`.

## Transcripts (`transcripts/`)

| File | Used by |
|------|---------|
| `baseline_01.txt` – `baseline_03.txt` | Day 1 baseline protocol |
| `tc01_in_scope_sync.txt` | TC-01 happy path |
| `tc02_discovery.txt` | TC-02 discovery / no SOW |
| `tc03_scope_creep.txt` | TC-03, TC-11 scope creep |
| `tc04_timeline_drift.txt` | TC-04 timeline conflict |
| `tc05_owner_ambiguity.txt` | TC-05 owner ambiguity |
| `tc06_short_call.txt` | TC-06 hallucination grader |
| `tc07_closing_signals.txt` | TC-07 CRM conflict |
| `tc12_garbled.txt` | TC-12 input validation |

## Accounts (`accounts/`)

- `acme_deal.json` — standard Acme Corp deal
- `acme_wrong_stage.json` — stage mismatch for TC-07
- `new_deal.json` — early-stage deal for TC-02

## SOW (`sow/`)

- `acme_web_app.txt` — Phase 1 web app scope (mobile excluded)

## Audio

TC-08 uses mock STT when `samples/audio/tc08_call.m4a` is absent.
