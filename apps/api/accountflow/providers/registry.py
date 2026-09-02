from accountflow.core.config import clear_settings_cache, get_settings, load_yaml_config
from accountflow.providers.base import LLMProvider, STTProvider
from accountflow.providers.deepgram import DeepgramSTTProvider
from accountflow.providers.gemini import GeminiProvider
from accountflow.providers.ollama_cloud import OllamaCloudProvider
from accountflow.providers.mock import MockLLMProvider, MockSTTProvider

_llm_cache: dict[str, LLMProvider] = {}
_stt_cache: dict[str, STTProvider] = {}

_LLM_ALIASES = {
    "ollama": "ollama_cloud",
    "ollama-cloud": "ollama_cloud",
}


def _normalize_llm_provider(name: str) -> str:
    return _LLM_ALIASES.get(name.strip().lower(), name.strip().lower())


def get_llm(name: str | None = None) -> LLMProvider:
    settings = get_settings()
    provider_name = _normalize_llm_provider(name or settings.llm_provider)
    if provider_name in _llm_cache:
        return _llm_cache[provider_name]

    if provider_name == "mock":
        provider: LLMProvider = MockLLMProvider()
    elif provider_name == "gemini":
        provider = GeminiProvider()
    elif provider_name == "ollama_cloud":
        provider = OllamaCloudProvider()
    else:
        valid = ", ".join(sorted({"mock", "gemini", "ollama_cloud", "ollama", *_LLM_ALIASES}))
        raise ValueError(f"Unknown LLM provider: {provider_name}. Valid: {valid}")

    _llm_cache[provider_name] = provider
    return provider


def get_stt(name: str | None = None) -> STTProvider:
    settings = get_settings()
    provider_name = name or settings.stt_provider
    if provider_name in _stt_cache:
        return _stt_cache[provider_name]

    if provider_name == "mock":
        provider: STTProvider = MockSTTProvider()
    elif provider_name == "deepgram":
        provider = DeepgramSTTProvider()
    else:
        raise ValueError(f"Unknown STT provider: {provider_name}")

    _stt_cache[provider_name] = provider
    return provider


def get_default_llm_name() -> str:
    yaml_cfg = load_yaml_config("providers.example.yaml")
    return yaml_cfg.get("llm", {}).get("default", get_settings().llm_provider)


def clear_provider_cache() -> None:
    clear_settings_cache()
    _llm_cache.clear()
    _stt_cache.clear()
