"""Request-scoped LLM override for BYOK (contextvar)."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from accountflow.providers.base import LLMProvider
from accountflow.providers.registry import get_llm

_llm_override: ContextVar[LLMProvider | None] = ContextVar("llm_override", default=None)


def get_request_llm() -> LLMProvider:
    override = _llm_override.get()
    if override is not None:
        return override
    return get_llm()


@contextmanager
def llm_override(provider: LLMProvider) -> Iterator[None]:
    token = _llm_override.set(provider)
    try:
        yield
    finally:
        _llm_override.reset(token)
