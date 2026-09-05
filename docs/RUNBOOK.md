# Operator Runbook — AccountFlow OS

**Audience:** Non-developer operator (Alex) + deployer (admin)

---

## For Alex (daily use)

### Before first use (one-time, ~10 min)
1. Admin completes setup (§ Admin below)
2. Open app URL → **Register** (or Google Sign-In)
3. Go to **Settings → Credentials** and paste your HubSpot, Jira, LLM, and Deepgram keys
4. Open **Connect** → authorize Gmail → select Jira project
5. (Optional) Upload SOW text per client for Scope Verifier

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
| Email didn't send | Check Gmail on Connect; draft in approval view |
| "not configured" / Settings error | Re-save keys under Settings → Credentials |
| Low confidence (yellow) | Edit field before Execute |

---

## For admin (setup — 3 steps)

### Step 1: Clone and configure
```bash
git clone <repo>
cd "Must Quest"
cp .env.example .env
# Set JWT_SECRET, CREDENTIALS_FERNET_KEY
# LLM_PROVIDER=mock / STT_PROVIDER=mock for demo
docker compose up --build
```

Generate a Fernet key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Step 2: OAuth apps (production)
- Google Cloud OAuth client with redirect URI matching `GOOGLE_REDIRECT_URI`
- Set `INTEGRATIONS_MOCK=false` so execute uses each user's vault keys
- Users bring their own HubSpot private app token, Jira API token, LLM/STT keys

### Step 3: Open UI
- Local: `http://localhost:3000` → Register / Sign in
- API docs: `http://localhost:8000/docs`

### Deploy
- **Vercel:** connect repo, set `NEXT_PUBLIC_API_URL` to Render API URL
- **Render:** deploy from `render.yaml`, add `JWT_SECRET`, `CREDENTIALS_FERNET_KEY`, Google OAuth secrets

---

## Privacy & consent

- Recording consent checkbox required before capture
- Do not record without informing participants
- User passwords are bcrypt-hashed; API keys are Fernet-encrypted at rest and never returned by the API

---

## Support escalation

- Run ID shown on approval page — provide when reporting issues
- Eval log: `python eval/run_eval.py`
