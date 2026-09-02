import os

import pytest

from accountflow.providers.registry import clear_provider_cache, get_llm, get_stt


@pytest.fixture(autouse=True)
def _clear():
    clear_provider_cache()
    yield
    clear_provider_cache()


def test_get_llm_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    clear_provider_cache()
    llm = get_llm()
    assert llm.name == "mock"


def test_get_stt_mock(monkeypatch):
    monkeypatch.setenv("STT_PROVIDER", "mock")
    clear_provider_cache()
    stt = get_stt()
    assert stt.name == "mock"


def test_unknown_llm_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unknown_provider")
    clear_provider_cache()
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_llm()
