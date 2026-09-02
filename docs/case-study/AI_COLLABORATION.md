# AI Collaboration Note

**Status:** Template — update throughout sprint, finalize Day 5

---

## Tools used

| Tool | Role |
|------|------|
| Cursor + Claude | Architecture, code generation, docs |
| LangGraph / OpenAI | Agent orchestration, LLM calls |
| Context7 | Library docs (LangGraph, Pydantic) |
| Deepgram/Whisper | Speech-to-text |
| HubSpot/Gmail/Jira APIs | Integrations |

---

## Work delegated to AI

- [ ] LangGraph workflow scaffold
- [ ] Pydantic schema definitions
- [ ] Scope Verifier prompt + grader logic
- [ ] FastAPI route boilerplate
- [ ] Next.js Approval Inbox components
- [ ] Test case fixtures and eval runner
- [ ] Documentation drafts

---

## How AI outputs were verified

- [ ] Pydantic validation on all structured outputs
- [ ] 12-case eval suite with pass/fail
- [ ] Manual review of 3+ failure cases
- [ ] Proxy user test (Day 3)
- [ ] Regression re-run after fixes (Day 4)
- [ ] Fresh-environment setup test (Day 5)

---

## Results rejected or manually corrected

| Item | AI suggested | Human decision | Why |
|------|--------------|----------------|-----|
| _example_ | Auto-send email | Rejected | Assessment requires approval gate |
| | | | |

_Fill during sprint._

---

## Core decisions owned personally

1. Product scope: 4-engine OS, not summarizer
2. Integration choices: HubSpot + Gmail + Jira (not Salesforce)
3. Scope Verifier as differentiator
4. Non-goals (no auto-send, no Zoom bot)
5. Eval rubric and test case design
6. Trade-offs documented in architecture
7. Final demo narrative and limitations
