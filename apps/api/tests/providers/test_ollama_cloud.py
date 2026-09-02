import pytest
from pytest_httpx import HTTPXMock

from accountflow.providers.ollama_cloud import OllamaCloudProvider, normalize_ollama_host
from accountflow.providers.registry import clear_provider_cache, get_llm


def test_normalize_ollama_host_strips_v1_suffix():
    assert normalize_ollama_host("https://ollama.com/v1") == "https://ollama.com"
    assert normalize_ollama_host("https://ollama.com") == "https://ollama.com"


def test_get_llm_ollama_alias(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_API_KEY", "test-key")
    clear_provider_cache()
    llm = get_llm()
    assert llm.name == "ollama_cloud"


@pytest.mark.asyncio
async def test_ollama_cloud_chat_api(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "test-key")
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://ollama.com/v1")
    monkeypatch.setenv("OLLAMA_MODEL", "gpt-oss:120b")
    clear_provider_cache()

    httpx_mock.add_response(
        url="https://ollama.com/api/chat",
        method="POST",
        json={"message": {"role": "assistant", "content": '{"flags": []}'}},
    )

    provider = OllamaCloudProvider()
    text = await provider.complete_text("system", "user")
    assert "flags" in text

    request = httpx_mock.get_request()
    assert request is not None
    assert request.url == "https://ollama.com/api/chat"
    assert request.headers["authorization"] == "Bearer test-key"
