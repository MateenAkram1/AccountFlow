import json
from typing import TypeVar

from pydantic import BaseModel

from accountflow.providers.base import LLMProvider, STTProvider
from accountflow.models.schemas import Transcript

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    name = "mock"

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self._responses = responses or {}

    async def complete_structured(
        self,
        schema: type[T],
        system: str,
        user: str,
    ) -> T:
        key = schema.__name__
        if key in self._responses:
            return schema.model_validate_json(self._responses[key])
        return schema.model_construct()

    async def complete_text(self, system: str, user: str) -> str:
        if "text" in self._responses:
            return self._responses["text"]
        lower = user.lower()
        if '"flags"' in user or "scope verification" in system.lower():
            transcript_part = user.split("Transcript:")[-1].lower() if "Transcript:" in user else lower
            flags = []
            if "mobile app" in transcript_part or "offline mode" in transcript_part:
                flags.append(
                    {
                        "type": "OUT_OF_SCOPE",
                        "request": "Mobile app with offline mode",
                        "evidence_quote": "mobile app",
                        "severity": "high",
                        "recommended_workflow": "change_request",
                    }
                )
            if "april" in transcript_part and "march" in lower:
                flags.append(
                    {
                        "type": "TIMELINE_DRIFT",
                        "request": "Client timeline moved to April",
                        "evidence_quote": "April",
                        "sow_reference": "March 31, 2026",
                        "severity": "medium",
                    }
                )
            if "api" in transcript_part:
                flags.append(
                    {
                        "type": "IN_SCOPE",
                        "request": "API integration",
                        "evidence_quote": "API",
                        "severity": "none",
                    }
                )
            return json.dumps({"flags": flags})
        if "summary" in lower and "emails" in lower:
            confidence = 0.55 if lower.count("ahmed") > 2 else 0.9
            owner = "TBD — review owners" if confidence < 0.7 else "Alex Rivera"
            return json.dumps(
                {
                    "summary": "Follow-up from client sync",
                    "emails": [
                        {
                            "mode": "external",
                            "to": ["sarah@acme.example"],
                            "subject": "Follow-up: Acme Corp",
                            "body": "Thank you for today's call.",
                            "evidence_quotes": ["follow-up"],
                        }
                    ],
                    "crm_updates": [
                        {
                            "field": "dealstage",
                            "value": "presentationscheduled",
                            "evidence_quote": "proposal",
                            "confidence": 0.85,
                        }
                    ],
                    "tasks": [
                        {
                            "summary": "Send API documentation",
                            "description": "Send REST API spec by Friday",
                            "owner": owner,
                            "due_date": "Friday",
                            "evidence_quote": "API spec this week",
                            "confidence": confidence,
                        }
                    ],
                }
            )
        return "mock response"


class MockSTTProvider(STTProvider):
    name = "mock"

    async def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> Transcript:
        return Transcript(text="Mock transcript from audio.", source="audio")
