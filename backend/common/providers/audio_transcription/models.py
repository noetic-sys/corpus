from typing import Optional
from pydantic import BaseModel

from .constants import AudioFormat


class TranscriptionRequest(BaseModel):
    """Request model for audio transcription."""

    audio_data: bytes
    audio_format: AudioFormat
    language: Optional[str] = None
    model: str = "whisper-1"
    response_format: str = "text"
