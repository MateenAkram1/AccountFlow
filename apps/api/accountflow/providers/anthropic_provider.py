"""Anthropic Messages API provider."""

from __future__ import annotations

import json
from typing import TypeVar

import httpx
from pydantic import BaseModel

from accountflow.providers.base import LLMProvider

T = TypeVar("T", bound=BaseModel)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        key = (api_key or "").strip()
        if not key:
            raise ValueError("Anthropic API key is required")
        self._api_key = key
        self._model = (model or "claude-sonnet-4-20250514").strip()

    async def _complete(self, system: str, user: str) -> str:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        payload = {
            "model": self._model,
            "max_tokens": 4096,
            "temperature": 0.2,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(ANTHROPIC_URL, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise ValueError(f"Anthropic error HTTP {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
        parts = data.get("content") or []
        texts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text"]
        if not texts:
            raise ValueError("Unexpected Anthropic response shape")
        return "\n".join(texts)

    async def complete_text(self, system: str, user: str) -> str:
        return await self._complete(system, user)

    async def complete_structured(
        self,
        schema: type[T],
        system: str,
        user: str,
    ) -> T:
        prompt = (
            f"{system}\n\nRespond with valid JSON matching this schema:\n"
            f"{json.dumps(schema.model_json_schema())}\n\nUser input:\n{user}"
        )
        raw = await self._complete(
            "You return only valid JSON. No markdown fences.",
            prompt,
        )
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return schema.model_validate_json(cleaned)
