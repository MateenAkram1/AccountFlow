# AI Collaboration Note

**Status:** Day 5 final  

---

## Tools used and role of each

| Tool | Role |
|------|------|
| Cursor (Composer / Claude) | Architecture drafts, implementation, docs, deploy scripts |
| LangGraph | Agent graph with interrupt for human approval |
| FastAPI + Pydantic | API, structured outputs, validation |
| Next.js 15 | Approval inbox and New Run UX |
| Context7 | Library docs (FastAPI/Vercel/HubSpot patterns) |
| Deepgram (and mock STT) | Speech-to-text for audio uploads |
| Multi-LLM registry (Gemini, OpenAI, Anthropic, Groq, Ollama Cloud, mock) | Drafting / scope verify via BYOK |
| HubSpot / Gmail / Jira APIs | Read deal context; execute after approve |
| Turso (libSQL) | Durable production database on Vercel |
| Agency agents (local clone) | Product Manager / UI / UX / Backend guidance for polish |

---

## Work delegated to AI

- [x] LangGraph workflow scaffold (scope → draft → grade → approve interrupt)  
- [x] Pydantic schemas for runs, scope flags, action packages  
- [x] Scope Verifier + hallucination grader logic  
- [x] FastAPI routes (auth, runs, integrations, SOWs)  
- [x] Next.js Approval Inbox / New Run / credentials UI  
- [x] Eval fixtures (`eval/test_cases.json`) and `eval/run_eval.py`  
- [x] Documentation drafts (architecture, runbook, case study shell)  
- [x] Deploy wiring (Vercel API + web, Turso env, HubSpot pipeline dropdowns)  

---

## How AI-generated results were verified

- [x] Pydantic validation on structured LLM outputs  
- [x] 12-case eval suite with pass/fail (`python eval/run_eval.py` → 12/12)  
- [x] Manual root-cause write-ups for ≥3 failures (`FAILURES.md`)  
- [x] Proxy baseline timing on three transcripts (`BASELINE.md`)  
- [x] Regression re-run after grader / owner-confidence / Gmail retry fixes  
- [x] Live deploy smoke checks (`/health`, CORS, login/session, HubSpot deal list)  

---

## Results rejected or manually corrected

| Item | AI suggested | Human decision | Why |
|------|--------------|----------------|-----|
| Auto-send email after draft | Ship without approve | **Rejected** | Assessment + real risk require human gate |
| Invite-only allowlist | Keep AUTH_ALLOWLIST enforced | **Removed** for open register | Product choice: anyone can register; BYOK holds secrets |
| Render free API | Primary production host | **Moved API to Vercel** | Render billing wall blocked free deploy |
| Local SQLite only on Vercel | “Fine for prod” | **Added Turso** | Redeploys wiped users, vault, connections |
| Cookie `SameSite=Lax` cross-subdomain | Default session cookie | **`SameSite=None; Secure`** | Web and API on different `*.vercel.app` hosts |
| Free-text HubSpot `dealstage` | Type stage strings | **Pipeline stage dropdowns** | HubSpot rejects invented IDs; UI must match portal |
| “Create sample deal” reuse first deal | Return existing if any | **Always create new** | User needed multiple deals for demos |
| Invented cost / P95 in RESULTS | Fill placeholder $ figures | **Left unmetered** | Only measured times and suite pass rate |

---

## Core decisions owned personally

1. Product is a **4-engine OS with approval**, not a meeting summarizer  
2. Integrations: **HubSpot + Gmail + Jira** (not Salesforce)  
3. **Scope Verifier** as the differentiator against naive ChatGPT  
4. Non-goals: no auto-send, no Zoom bot, English-only v1  
5. Eval rubric and the 12 test cases  
6. Architecture trade-offs (transcript-in, BYOK, Turso)  
7. Demo narrative: 38 → 6 minutes, 12/12 suite, honest limitations  
