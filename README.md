# Must Quest — AccountFlow OS

AI OS Mini for the 5-Day Remote AI OS Sprint.

**Problem:** After client calls, reps spend 30–40 min on follow-up emails, CRM updates, and tasks — often missing out-of-scope requests.

**System:** Record/upload meeting + HubSpot context + SOW → Scope Verifier → human approves → executes via Gmail, HubSpot, Jira.

**User (proxy):** Alex Rivera, AE/PM — see `docs/workflow/USER.md`

---

## Quick start (3 steps)

```bash
# 1. Configure secrets
cp .env.example .env
# Set LLM_PROVIDER=mock for offline dev, or GEMINI_API_KEY for live

# 2. API (use project venv)
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
# source .venv/bin/activate    # macOS/Linux
pip install -e ".[dev]"
uvicorn accountflow.main:app --reload --port 8000

# 3. Web (new terminal)
cd apps/web && npm install && npm run dev
# Open http://localhost:3000
```

Or from repo root: `make install && make run-api` (terminal 1) + `make run-web` (terminal 2).

Docker: `docker compose up --build`

---

## Monorepo layout

| Path | Purpose |
|------|---------|
| `apps/api/` | FastAPI + LangGraph backend |
| `apps/web/` | Next.js 15 Approval Inbox |
| `config/` | Provider + app YAML examples |
| `samples/` | Synthetic transcripts, SOW, accounts |
| `eval/` | 12-case test suite + `run_eval.py` |

---

## Deploy (free tier)

| Service | Target |
|---------|--------|
| **Web** | Vercel Hobby — root `vercel.json` → `apps/web` |
| **API** | Render free — `render.yaml` → `apps/api` |
| **Env** | `NEXT_PUBLIC_API_URL` on Vercel → Render API URL |

---

## Docs

| Doc | Purpose |
|-----|---------|
| [docs/SPRINT.md](docs/SPRINT.md) | 5-day implementation plan |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Locked scope + stack |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Operator guide |
| [docs/evaluation/](docs/evaluation/) | Baseline, metrics, results |

---

## CLI

```bash
cd apps/api
python -m accountflow.cli run \
  --transcript ../../samples/transcripts/tc01_in_scope_sync.txt \
  --account ../../samples/accounts/acme_deal.json \
  --sow ../../samples/sow/acme_web_app.txt \
  --llm mock
```

## Eval

```bash
make eval
# or: python eval/run_eval.py
```
