# Operator Runbook — AccountFlow OS

**Audience:** Non-developer operator (Alex) + deployer (admin)

---

## For Alex (daily use)

### Before first use (one-time, ~10 min)
1. Admin completes setup (§ Admin below)
2. Open app URL → **New Run**
3. Upload SOW text for each active client (optional but enables Scope Verifier)

### After every client call
1. Go to **New Run**
2. Check **recording consent** → **Record** OR paste transcript
3. Wait for processing (~30–60 sec)
4. Review **Approval Inbox** (`/runs/{id}`):
   - Check **Scope Verifier** flags (red = out of scope)
   - Review email / CRM fields / tasks
5. Click **Approve all**
6. Click **Execute**
7. Confirm green checkmarks in execution log

### If something goes wrong
| Symptom | Action |
|---------|--------|
| "insufficient_content" | Re-upload clearer transcript or re-record |
| Scope flag seems wrong | Edit tasks/email before Execute |
| Email didn't send | Check Gmail OAuth (admin); draft in approval view |
| Low confidence (yellow) | Edit field before Execute |

---

## For admin (setup — 3 steps)

### Step 1: Clone and configure
```bash
git clone <repo>
cd "Must Quest"
cp .env.example .env
# LLM_PROVIDER=mock for demo; GEMINI_API_KEY + DEEPGRAM_API_KEY for live
docker compose up --build
```

### Step 2: OAuth apps (production)
- HubSpot developer app (`crm.objects.deals.read/write`)
- Google Cloud (Gmail send scope)
- Jira API token (create issues)
- Set `INTEGRATIONS_MOCK=false` in `.env`

### Step 3: Open UI
- Local: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`

### Deploy
- **Vercel:** connect repo, set `NEXT_PUBLIC_API_URL` to Render API URL
- **Render:** deploy from `render.yaml`, add secrets in dashboard

---

## Privacy & consent

- Recording consent checkbox required before capture
- Do not record without informing participants

---

## Support escalation

- Run ID shown on approval page — provide when reporting issues
- Eval log: `python eval/run_eval.py`
