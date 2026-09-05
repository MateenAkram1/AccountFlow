"""Per-user BYOK credential APIs — write-only / status-only."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from accountflow.api.deps import CurrentUser, get_current_user, require_csrf
from accountflow.db.vault import VALID_PROVIDERS, get_secrets_vault

router = APIRouter(prefix="/me", tags=["me"])


class HubSpotCredentials(BaseModel):
    access_token: str = Field(..., min_length=10, json_schema_extra={"writeOnly": True})


class JiraCredentials(BaseModel):
    site_url: str = Field(..., min_length=8)
    email: str = Field(..., min_length=3)
    api_token: str = Field(..., min_length=8, json_schema_extra={"writeOnly": True})


class LlmCredentials(BaseModel):
    provider: Literal[
        "gemini", "ollama_cloud", "ollama", "openai", "anthropic", "groq", "mock"
    ] = "gemini"
    api_key: str | None = Field(default=None, json_schema_extra={"writeOnly": True})
    base_url: str | None = None
    model: str | None = None


class SttCredentials(BaseModel):
    provider: Literal["deepgram", "mock"] = "deepgram"
    api_key: str | None = Field(default=None, json_schema_extra={"writeOnly": True})


@router.get("")
async def get_me(user: CurrentUser = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "name": user.name}


@router.get("/credentials/status")
async def credentials_status(user: CurrentUser = Depends(get_current_user)):
    return get_secrets_vault().status(user.id)


@router.put("/credentials/{provider}")
async def put_credentials(
    provider: str,
    body: dict[str, Any],
    user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=404, detail="Unknown provider")

    vault = get_secrets_vault()
    try:
        if provider == "hubspot":
            parsed = HubSpotCredentials.model_validate(body)
            payload = {"access_token": parsed.access_token.strip()}
        elif provider == "jira":
            parsed_j = JiraCredentials.model_validate(body)
            payload = {
                "site_url": parsed_j.site_url.strip().rstrip("/"),
                "email": parsed_j.email.strip(),
                "api_token": parsed_j.api_token.strip(),
            }
        elif provider == "llm":
            parsed_l = LlmCredentials.model_validate(body)
            if parsed_l.provider != "mock" and not (parsed_l.api_key or "").strip():
                raise HTTPException(status_code=400, detail="api_key required for this LLM provider")
            payload = {
                "provider": parsed_l.provider,
                "api_key": (parsed_l.api_key or "").strip(),
                "base_url": parsed_l.base_url,
                "model": parsed_l.model,
            }
        else:  # stt
            parsed_s = SttCredentials.model_validate(body)
            if parsed_s.provider != "mock" and not (parsed_s.api_key or "").strip():
                raise HTTPException(status_code=400, detail="api_key required for this STT provider")
            payload = {
                "provider": parsed_s.provider,
                "api_key": (parsed_s.api_key or "").strip(),
            }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    vault.put(user.id, provider, payload)
    return {"ok": True, "provider": provider, "configured": True}


@router.delete("/credentials/{provider}")
async def delete_credentials(
    provider: str,
    user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=404, detail="Unknown provider")
    get_secrets_vault().delete(user.id, provider)
    return {"ok": True, "provider": provider}
