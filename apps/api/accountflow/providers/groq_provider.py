"""Groq OpenAI-compatible chat completions (fast inference)."""

from __future__ import annotations

from accountflow.providers.openai_provider import OpenAIProvider


class GroqProvider(OpenAIProvider):
    name = "groq"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model or "llama-3.3-70b-versatile",
            base_url=base_url or "https://api.groq.com/openai/v1",
        )
