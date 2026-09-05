"""OpenAI Chat Completions provider (latest SDK-compatible HTTP API)."""

from __future__ import annotations

import json
from typing import TypeVar

import httpx
from pydantic import BaseModel

from accountflow.providers.base import LLMProvider

T = TypeVar("T", bound=BaseModel)

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        key = (api_key or "").strip()
        if not key:
            raise ValueError("OpenAI API key is required")
        self._api_key = key
        self._model = (model or "gpt-4o-mini").strip()
        base = (base_url or "https://api.openai.com/v1").rstrip("/")
        self._url = f"{base}/chat/completions"

    async def _complete(self, system: str, user: str) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(self._url, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise ValueError(f"OpenAI error HTTP {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Unexpected OpenAI response shape") from exc

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
