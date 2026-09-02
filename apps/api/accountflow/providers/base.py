from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from accountflow.models.schemas import Transcript

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def complete_structured(
        self,
        schema: type[T],
        system: str,
        user: str,
    ) -> T:
        ...

    @abstractmethod
    async def complete_text(self, system: str, user: str) -> str:
        ...


class STTProvider(ABC):
    name: str

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> Transcript:
        ...
