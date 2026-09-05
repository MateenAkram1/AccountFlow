import io

from deepgram import DeepgramClient

from accountflow.core.config import get_settings
from accountflow.models.schemas import Transcript
from accountflow.providers.base import STTProvider


class DeepgramSTTProvider(STTProvider):
    name = "deepgram"

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        key = (api_key or settings.deepgram_api_key or "").strip()
        if not key:
            raise ValueError("DEEPGRAM_API_KEY is required for deepgram STT provider")
        self._client = DeepgramClient(api_key=key)
        self._model = "nova-2"

    async def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> Transcript:
        buffer = io.BytesIO(audio_bytes)
        response = self._client.listen.v1.media.transcribe_file(
            request=buffer.read(),
            model=self._model,
            smart_format=True,
            punctuate=True,
        )
        text = ""
        if response and response.results and response.results.channels:
            alt = response.results.channels[0].alternatives
            if alt:
                text = alt[0].transcript or ""
        return Transcript(text=text.strip(), source="audio")
