# Locked Decisions — AccountFlow OS

## Product
Meeting + account context → scope verify → approve → execute (Gmail, HubSpot, Jira)

## User (proxy)
Alex Rivera — AE/PM, 8–12 client calls/week, HubSpot + Gmail + Jira

## Primary metric
Time call end → email sent + CRM updated (**target <8 min** vs 30–40 manual)

## Stack
Python 3.11+ · LangGraph · FastAPI · Next.js 15 · SQLite (dev) / Turso libSQL (prod)  
**AI:** Gemini (default LLM) · Ollama Cloud (fallback) · Deepgram (STT)  
**Deploy:** Vercel (web + API) · Turso libSQL (prod DB)

## Integrations
| Ingest | Execute |
|--------|---------|
| Record/upload + STT | Gmail send |
| HubSpot read | HubSpot write |
| SOW upload | Jira create |

## Non-goals (v1)
1. No auto-send without approval  
2. No Zoom/Meet bot  
3. No Salesforce  
4. No org/billing SaaS layer (open register + per-user BYOK)  
5. English-only  

## Auth & credentials
- Open registration: Google Sign-In **or** email/password (bcrypt)
- Session: HttpOnly JWT cookie
- Per-user Fernet-encrypted credential vault (HubSpot, Jira, LLM, STT); Gmail OAuth tokens encrypted per user
- No runtime fallback to shared operator `.env` API keys for logged-in users

## Human vs AI
- **AI:** transcribe, extract, scope flag, draft  
- **Human:** approve every execute action  
