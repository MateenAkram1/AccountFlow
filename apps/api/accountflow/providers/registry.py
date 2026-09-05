from accountflow.core.config import clear_settings_cache, get_settings, load_yaml_config
from accountflow.providers.anthropic_provider import AnthropicProvider
from accountflow.providers.base import LLMProvider, STTProvider
from accountflow.providers.deepgram import DeepgramSTTProvider
from accountflow.providers.gemini import GeminiProvider
from accountflow.providers.groq_provider import GroqProvider
from accountflow.providers.mock import MockLLMProvider, MockSTTProvider
from accountflow.providers.ollama_cloud import OllamaCloudProvider
from accountflow.providers.openai_provider import OpenAIProvider

_llm_cache: dict[str, LLMProvider] = {}
_stt_cache: dict[str, STTProvider] = {}

_LLM_ALIASES = {
    "ollama": "ollama_cloud",
    "ollama-cloud": "ollama_cloud",
    "gpt": "openai",
    "chatgpt": "openai",
    "claude": "anthropic",
}

VALID_LLM_PROVIDERS = frozenset(
    {"mock", "gemini", "ollama_cloud", "openai", "anthropic", "groq"}
)


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
    elif provider_name == "openai":
        key = (settings.openai_api_key or "").strip()
        if not key:
            raise ValueError("OPENAI_API_KEY is required for openai provider")
        provider = OpenAIProvider(api_key=key, model=settings.openai_model or None)
    elif provider_name == "anthropic":
        key = (settings.anthropic_api_key or "").strip()
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is required for anthropic provider")
        provider = AnthropicProvider(api_key=key, model=settings.anthropic_model or None)
    elif provider_name == "groq":
        key = (settings.groq_api_key or "").strip()
        if not key:
            raise ValueError("GROQ_API_KEY is required for groq provider")
        provider = GroqProvider(api_key=key, model=settings.groq_model or None)
    else:
        valid = ", ".join(sorted(VALID_LLM_PROVIDERS | set(_LLM_ALIASES)))
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
