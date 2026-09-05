"""Resolve per-user BYOK credentials for integrations and providers."""

from __future__ import annotations

from typing import Any

from accountflow.core.config import get_settings
from accountflow.db.tokens import get_token_store
from accountflow.db.vault import get_secrets_vault
from accountflow.integrations.gmail import GmailClient
from accountflow.integrations.hubspot import HubSpotClient
from accountflow.integrations.jira import JiraClient
from accountflow.providers.anthropic_provider import AnthropicProvider
from accountflow.providers.base import LLMProvider, STTProvider
from accountflow.providers.deepgram import DeepgramSTTProvider
from accountflow.providers.gemini import GeminiProvider
from accountflow.providers.groq_provider import GroqProvider
from accountflow.providers.mock import MockLLMProvider, MockSTTProvider
from accountflow.providers.ollama_cloud import OllamaCloudProvider
from accountflow.providers.openai_provider import OpenAIProvider
from accountflow.providers.registry import _normalize_llm_provider


class CredentialsMissing(ValueError):
    """User must configure credentials in Settings."""


def _missing(msg: str) -> CredentialsMissing:
    return CredentialsMissing(msg)


def hubspot_client_for_user(user_id: str) -> HubSpotClient:
    settings = get_settings()
    if settings.integrations_mock:
        return HubSpotClient(access_token="mock")
    payload = get_secrets_vault().get(user_id, "hubspot")
    token = (payload or {}).get("access_token") if payload else None
    if not token:
        raise _missing("HubSpot not configured. Add your token in Settings → Credentials.")
    return HubSpotClient(access_token=token, allow_env_fallback=False)


def jira_client_for_user(user_id: str, project_key: str | None = None) -> JiraClient:
    settings = get_settings()
    if settings.integrations_mock:
        return JiraClient(
            project_key=project_key or "DEMO",
            site_url="https://mock.atlassian.net",
            email="mock@example.com",
            api_token="mock",
            user_id=user_id,
            allow_env_fallback=False,
        )
    payload = get_secrets_vault().get(user_id, "jira")
    if not payload:
        raise _missing("Jira not configured. Add your site URL, email, and API token in Settings.")
    return JiraClient(
        project_key=project_key,
        site_url=payload.get("site_url"),
        email=payload.get("email"),
        api_token=payload.get("api_token"),
        user_id=user_id,
        allow_env_fallback=False,
    )


def gmail_client_for_user(user_id: str) -> GmailClient:
    return GmailClient(user_id=user_id, allow_env_fallback=False)


def llm_for_user(user_id: str) -> LLMProvider:
    settings = get_settings()
    payload = get_secrets_vault().get(user_id, "llm")
    if payload:
        name = _normalize_llm_provider(payload.get("provider") or "mock")
        key = (payload.get("api_key") or "").strip()
        model = payload.get("model")
        base_url = payload.get("base_url")
        if name == "mock":
            return MockLLMProvider()
        if name == "gemini":
            if not key:
                raise _missing("LLM Gemini API key missing. Update Settings → Credentials.")
            return GeminiProvider(api_key=key)
        if name == "ollama_cloud":
            if not key:
                raise _missing("Ollama API key missing. Update Settings → Credentials.")
            return OllamaCloudProvider(api_key=key, base_url=base_url, model=model)
        if name == "openai":
            if not key:
                raise _missing("OpenAI API key missing. Update Settings → Credentials.")
            return OpenAIProvider(api_key=key, model=model, base_url=base_url)
        if name == "anthropic":
            if not key:
                raise _missing("Anthropic API key missing. Update Settings → Credentials.")
            return AnthropicProvider(api_key=key, model=model)
        if name == "groq":
            if not key:
                raise _missing("Groq API key missing. Update Settings → Credentials.")
            return GroqProvider(api_key=key, model=model, base_url=base_url)
        raise _missing(f"Unknown LLM provider in vault: {name}")

    if _normalize_llm_provider(settings.llm_provider) == "mock":
        return MockLLMProvider()
    raise _missing(
        "LLM credentials not configured. Add your API key in Settings → Credentials "
        "(or set LLM_PROVIDER=mock for demos)."
    )


def stt_for_user(user_id: str) -> STTProvider:
    settings = get_settings()
    payload = get_secrets_vault().get(user_id, "stt")
    if payload:
        name = (payload.get("provider") or "mock").strip().lower()
        if name == "mock":
            return MockSTTProvider()
        if name == "deepgram":
            key = (payload.get("api_key") or "").strip()
            if not key:
                raise _missing("Deepgram API key missing. Update Settings → Credentials.")
            return DeepgramSTTProvider(api_key=key)
        raise _missing(f"Unknown STT provider in vault: {name}")

    if (settings.stt_provider or "").strip().lower() == "mock":
        return MockSTTProvider()
    raise _missing(
        "STT credentials not configured. Add Deepgram in Settings → Credentials "
        "(or set STT_PROVIDER=mock for demos)."
    )


def integration_status_for_user(user_id: str) -> dict[str, Any]:
    settings = get_settings()
    vault = get_secrets_vault()
    tokens = get_token_store()
    google_connected = tokens.has(user_id, "google")
    jira_payload = vault.get(user_id, "jira") if vault.has(user_id, "jira") else None
    selected = JiraClient.get_selected_project(user_id)
    return {
        "mock_mode": settings.integrations_mock,
        "hubspot": {
            "configured": vault.has(user_id, "hubspot") or settings.integrations_mock,
            "mode": "vault" if vault.has(user_id, "hubspot") else (
                "mock" if settings.integrations_mock else "missing"
            ),
        },
        "gmail": {
            "oauth_app_configured": settings.google_oauth_configured,
            "connected": google_connected or settings.integrations_mock,
            "connect_url": "/auth/google/gmail/start" if settings.google_oauth_configured else None,
        },
        "jira": {
            "configured": bool(jira_payload) or settings.integrations_mock,
            "selected_project": selected,
        },
    }
