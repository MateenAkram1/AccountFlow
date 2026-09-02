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
**Deploy:** Vercel (web) · Render free (API)

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
4. No multi-tenant SaaS  
5. English-only  

## Human vs AI
- **AI:** transcribe, extract, scope flag, draft  
- **Human:** approve every execute action  
