from abc import ABC, abstractmethod
from typing import Optional

from .constants import AudioFormat


class AudioTranscriptionInterface(ABC):
    """Interface for audio transcription providers."""

    @abstractmethod
    async def transcribe_audio_bytes(
        self,
        audio_data: bytes,
        audio_format: AudioFormat,
        language: Optional[str] = None,
    ) -> str:
        """
        Transcribe audio data from bytes.

        Args:
            audio_data: The audio file data as bytes
            audio_format: The audio file format
            language: Optional language code for transcription (e.g., 'en-US')

        Returns:
            The transcribed text as a string
        """
        pass

    @abstractmethod
    async def transcribe_audio_uri(
        self,
        storage_uri: str,
        audio_format: AudioFormat,
        language: Optional[str] = None,
    ) -> str:
        """
        Transcribe audio data from storage URI.

        Args:
            storage_uri: The storage URI (e.g., 'gs://bucket/file', 's3://bucket/file')
            audio_format: The audio file format
            language: Optional language code for transcription (e.g., 'en-US')

        Returns:
            The transcribed text as a string
        """
        pass

    @abstractmethod
    def supports_format(self, audio_format: AudioFormat) -> bool:
        """
        Check if the provider supports the given audio format.

        Args:
            audio_format: The audio file format to check

        Returns:
            True if format is supported, False otherwise
        """
        pass
