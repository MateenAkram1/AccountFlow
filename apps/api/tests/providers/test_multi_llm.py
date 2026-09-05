"""Smoke tests for multi-provider LLM registry wiring."""

import pytest

from accountflow.providers.anthropic_provider import AnthropicProvider
from accountflow.providers.groq_provider import GroqProvider
from accountflow.providers.openai_provider import OpenAIProvider
from accountflow.providers.registry import VALID_LLM_PROVIDERS, _normalize_llm_provider, get_llm
from accountflow.providers.registry import clear_provider_cache


def test_normalize_aliases():
    assert _normalize_llm_provider("claude") == "anthropic"
    assert _normalize_llm_provider("gpt") == "openai"
    assert _normalize_llm_provider("ollama") == "ollama_cloud"


def test_valid_providers_include_new_vendors():
    assert {"openai", "anthropic", "groq", "gemini", "ollama_cloud", "mock"} <= VALID_LLM_PROVIDERS


def test_openai_provider_requires_key():
    with pytest.raises(ValueError, match="API key"):
        OpenAIProvider(api_key="")


def test_anthropic_provider_requires_key():
    with pytest.raises(ValueError, match="API key"):
        AnthropicProvider(api_key="")


def test_groq_defaults_base(monkeypatch):
    p = GroqProvider(api_key="gsk_test")
    assert "groq.com" in p._url
    assert "llama" in p._model


def test_mock_still_works(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    clear_provider_cache()
    llm = get_llm("mock")
    assert llm.name == "mock"
