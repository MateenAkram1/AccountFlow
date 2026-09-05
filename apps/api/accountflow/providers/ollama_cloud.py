import json
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from accountflow.core.config import get_settings
from accountflow.providers.base import LLMProvider

T = TypeVar("T", bound=BaseModel)


def normalize_ollama_host(base_url: str) -> str:
    """Ollama Cloud uses https://ollama.com/api/chat (not OpenAI /v1)."""
    host = base_url.strip().rstrip("/")
    if host.endswith("/v1"):
        host = host[:-3]
    return host


class OllamaCloudProvider(LLMProvider):
    """Ollama Cloud — native API at https://ollama.com/api/chat."""

    name = "ollama_cloud"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        settings = get_settings()
        key = (api_key or settings.ollama_cloud_api_key or "").strip()
        if not key:
            raise ValueError(
                "OLLAMA_API_KEY (or OLLAMA_CLOUD_API_KEY) is required for ollama_cloud provider"
            )
        self._host = normalize_ollama_host(base_url or settings.ollama_cloud_base_url)
        self._model = model or settings.ollama_cloud_model
        self._api_key = key

    async def complete_structured(
        self,
        schema: type[T],
        system: str,
        user: str,
    ) -> T:
        text = await self.complete_text(
            f"{system}\nRespond with valid JSON only matching the requested schema.",
            f"{user}\n\nSchema:\n{json.dumps(schema.model_json_schema())}",
        )
        cleaned = _extract_json(text)
        return schema.model_validate_json(cleaned)

    async def complete_text(self, system: str, user: str) -> str:
        messages: list[dict[str, str]] = []
        if system.strip():
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        url = f"{self._host}/api/chat"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
            except httpx.HTTPError as exc:
                raise ValueError(f"Ollama Cloud request failed: {exc}") from exc

            if response.status_code == 401:
                raise ValueError("Ollama Cloud authentication failed — check OLLAMA_API_KEY")
            if response.status_code == 404:
                raise ValueError(
                    f"Ollama model '{self._model}' not found on {self._host}. "
                    f"List available models: GET {self._host}/api/tags"
                )
            if response.status_code >= 400:
                detail = _response_detail(response)
                raise ValueError(
                    f"Ollama Cloud error {response.status_code} for model '{self._model}': {detail}"
                )

            data = response.json()
            content = _parse_chat_content(data)
            if not content:
                raise ValueError("Ollama Cloud returned an empty response")
            return content


def _parse_chat_content(data: dict[str, Any]) -> str:
    message = data.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content
    response = data.get("response")
    if isinstance(response, str) and response.strip():
        return response
    return ""


def _response_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict):
            return str(body.get("error") or body.get("message") or body)
    except ValueError:
        pass
    text = response.text.strip()
    return text[:300] if text else response.reason_phrase


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()
