# Operator Runbook — AccountFlow OS

**Audience:** Non-developer operator (Alex) + deployer (admin)

**Live web:** https://accountflow-web.vercel.app  
**Live API:** https://accountflow-api.vercel.app  

**Demo fixtures:** `samples/demo/demo_meeting_transcript.txt`, `samples/demo/demo_sow.txt`

---

## For Alex (daily use)

### Before first use (one-time, ~10 min)
1. Admin completes setup (§ Admin below) **or** use the live URLs above
2. Open app → **Register** (or Google Sign-In)
3. Go to **Settings → Credentials** and paste your HubSpot, Jira, LLM, and Deepgram keys
4. Open **Connect** → authorize Gmail → select Jira project
5. (Optional) Upload SOW text per client for Scope Verifier

### After every client call
1. Go to **New Run**
2. Select or create a HubSpot deal; attach SOW
3. Check **recording consent** → **Record** OR paste transcript (try `samples/demo/`)
4. Wait for processing (~30–60 sec)
5. Review **Approval Inbox** (`/runs/{id}`):
   - Check **Scope Verifier** flags (red = out of scope)
   - Review email / CRM fields (stage dropdown) / tasks
6. Click **Approve all**
7. Click **Execute**
8. Confirm green checkmarks in execution log

### If something goes wrong
| Symptom | Action |
|---------|--------|
| "insufficient_content" | Re-upload clearer transcript or re-record |
| Scope flag seems wrong | Edit tasks/email before Execute |
| Email didn't send | Check Gmail on Connect; draft in approval view |
| "not configured" / Settings error | Re-save keys under Settings → Credentials |
| Low confidence (yellow) | Edit field before Execute |
| Logged out after idle / bounce to sign-in | Sign in again; data persists on Turso in prod |

---

## For admin (setup — 3 steps)

### Step 1: Clone and configure
```bash
git clone <repo>
cd "Must Quest"
cp .env.example .env
# Set JWT_SECRET, CREDENTIALS_FERNET_KEY
# LLM_PROVIDER=mock / STT_PROVIDER=mock for demo
# Optional prod: TURSO_DATABASE_URL, TURSO_AUTH_TOKEN
docker compose up --build
```

Generate a Fernet key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Step 2: OAuth apps (production)
- Google Cloud OAuth client with redirect URI matching `GOOGLE_REDIRECT_URI`
  - Prod example: `https://accountflow-api.vercel.app/auth/google/callback`
- Set `INTEGRATIONS_MOCK=false` so execute uses each user's vault keys
- Users bring their own HubSpot private app token, Jira API token, LLM/STT keys

### Step 3: Open UI
- Local: `http://localhost:3000` → Register / Sign in
- API docs: `http://localhost:8000/docs`
- Live: https://accountflow-web.vercel.app

### Deploy (Vercel)
- **API** project → `apps/api`: set `JWT_SECRET`, `CREDENTIALS_FERNET_KEY`, Google OAuth, `CORS_ORIGINS` / `WEB_APP_URL`, Turso vars
- **Web** project → `apps/web`: set `NEXT_PUBLIC_API_URL=https://accountflow-api.vercel.app`
- Cookies: production uses `SameSite=None; Secure` so web and API can share session across subdomains

---

## Privacy & consent

- Recording consent checkbox required before capture
- Do not record without informing participants
- User passwords are bcrypt-hashed; API keys are Fernet-encrypted at rest and never returned by the API

---

## Support escalation

- Run ID shown on approval page — provide when reporting issues
- Eval log: `python eval/run_eval.py`
- Submission pack: `python scripts/build_submission_pack.py` → `docs/submission/`
