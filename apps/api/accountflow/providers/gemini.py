import json
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from accountflow.core.config import get_settings
from accountflow.providers.base import LLMProvider

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        key = (api_key or settings.gemini_api_key or "").strip()
        if not key:
            raise ValueError("GEMINI_API_KEY is required for gemini provider")
        self._client = genai.Client(api_key=key)
        self._model = "gemini-2.0-flash"

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
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        text = response.text or "{}"
        return schema.model_validate_json(text)

    async def complete_text(self, system: str, user: str) -> str:
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=f"{system}\n\n{user}",
            config=types.GenerateContentConfig(temperature=0.3),
        )
        return response.text or ""
