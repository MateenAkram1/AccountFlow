# Demo Video Script (5 minutes)

**Live web:** https://accountflow-web.vercel.app  
**Live API:** https://accountflow-api.vercel.app  

**Requirement:** Problem, baseline, live flow, non-dev UX, evaluation, key limitation  

**Preferred fixtures:**  
- Transcript: `samples/demo/demo_meeting_transcript.txt` (full path) **or** short creep demo `samples/transcripts/tc03_scope_creep.txt`  
- SOW: `samples/demo/demo_sow.txt` **or** `samples/sow/acme_web_app.txt`  

---

## [0:00–0:45] Problem & baseline (45 sec)

**Say:**
> "Alex runs about ten client calls a week. After each one she spent roughly 38 minutes updating HubSpot, writing the follow-up, and filing Jira — and still missed scope creep. ChatGPT cut draft time to about 22 minutes but still needed copy-paste into tools and never checked the SOW."

**Show:** Timing table from `docs/evaluation/BASELINE.md` (38 / 22 / 6).

---

## [0:45–1:15] What we built (30 sec)

**Say:**
> "AccountFlow OS takes the transcript, the HubSpot deal, and the SOW. It flags scope issues, drafts email, CRM, and tasks, and only after Alex approves does it send Gmail, update HubSpot, and create Jira."

**Show:** Homepage → New Run / Approvals flow (or architecture one-liner).

---

## [1:15–3:30] Live flow — non-dev UX (2 min 15 sec)

1. Open https://accountflow-web.vercel.app — sign in.  
2. **New Run** → select or **create** a HubSpot deal (show stage dropdown).  
3. Paste demo transcript + attach demo SOW (or upload files).  
4. Process → open run: show **OUT_OF_SCOPE** / timeline flags if present.  
5. **Approval Inbox:** field dropdowns for CRM stage (HubSpot labels), edit one email line, approve sections.  
6. **Execute** → show execution log (mock or live).  

**Emphasize:** "Nothing executes without approval."

---

## [3:30–4:15] Evaluation & failure handling (45 sec)

**Show / say:**
- `python eval/run_eval.py` → **12/12 PASS** (`docs/evaluation/RESULTS.md`)  
- One failure we caught: short-call invented deadline (**TC-06**) — grader + human approve  
- Measured path: **38 → 6 minutes** mean on baseline transcripts (mock)  

---

## [4:15–5:00] Limitation & next steps (45 sec)

**Say:**
> "Biggest limitation: Scope Verifier is only as good as the SOW you attach, and we still require a human for every send. Owner confidence drops when two people share a name — we force review. Next two weeks: five live calls with the proxy user, cost logging, and tighter SOW parsing."

**Show:** Case study §8 two-week plan.

---

## Recording checklist

- [ ] Live site loads: https://accountflow-web.vercel.app  
- [ ] Credentials / Connect configured for the demo account (or mock path explained)  
- [ ] Sample data only (demo transcript/SOW — no real client PII)  
- [ ] Demo path: New Run → transcript + SOW → Approve → Execute  
- [ ] Show run id and at least one scope flag  
- [ ] Cite **38 → 6 min** and **12/12** only (no invented $ cost)  
- [ ] 5:00 or under  
