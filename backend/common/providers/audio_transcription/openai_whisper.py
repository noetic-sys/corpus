import io
from typing import Optional
from openai import AsyncOpenAI

from .interface import AudioTranscriptionInterface
from .constants import AudioFormat
from common.core.otel_axiom_exporter import get_logger
from common.providers.api_keys.factory import get_rotator
from common.providers.api_keys.provider_enum import APIProviderType

logger = get_logger(__name__)


class OpenAIWhisperProvider(AudioTranscriptionInterface):
    """OpenAI Whisper transcription provider."""

    SUPPORTED_FORMATS = {
        AudioFormat.MP3,
        AudioFormat.WAV,
        AudioFormat.FLAC,
        AudioFormat.M4A,
        AudioFormat.OGG,
        AudioFormat.WEBM,
    }

    def __init__(self):
        self.rotator = get_rotator(APIProviderType.OPENAI)
        if not self.rotator:
            raise ValueError("OpenAI API keys not configured")

    def supports_format(self, audio_format: AudioFormat) -> bool:
        """Check if the provider supports the given audio format."""
        return audio_format in self.SUPPORTED_FORMATS

    async def transcribe_audio_bytes(
        self,
        audio_data: bytes,
        audio_format: AudioFormat,
        language: Optional[str] = None,
    ) -> str:
        """
        Transcribe audio data using OpenAI Whisper.

        Args:
            audio_data: The audio file data as bytes
            audio_format: The audio file format
            language: Optional language code (ISO-639-1 format, e.g., 'en')

        Returns:
            The transcribed text as a string
        """
        if not self.supports_format(audio_format):
            raise ValueError(f"Unsupported audio format: {audio_format}")

        # Get rotated API key
        api_key = self.rotator.get_next_key()
        client = AsyncOpenAI(api_key=api_key)

        try:
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"audio.{audio_format.value}"

            logger.info(
                f"Starting OpenAI Whisper transcription for {audio_format.value} audio"
            )

            response = await client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                language=language,
                response_format="text",
            )

            # Report success
            self.rotator.report_success(api_key)

            transcript = (
                response.strip() if isinstance(response, str) else str(response).strip()
            )

            logger.info(
                f"OpenAI Whisper transcription completed: {len(transcript)} characters"
            )
            return transcript

        except Exception as e:
            # Report failure
            self.rotator.report_failure(api_key)

            logger.error(f"Error in OpenAI Whisper transcription: {e}")
            raise Exception(f"Failed to transcribe audio: {str(e)}")

    async def transcribe_audio_uri(
        self,
        storage_uri: str,
        audio_format: AudioFormat,
        language: Optional[str] = None,
    ) -> str:
        """
        OpenAI Whisper does not support transcription from storage URIs.

        Args:
            storage_uri: The storage URI
            audio_format: The audio file format
            language: Optional language code

        Raises:
            NotImplementedError: OpenAI Whisper only supports bytes input
        """
        raise NotImplementedError(
            "OpenAI Whisper provider does not support storage URI transcription"
        )
