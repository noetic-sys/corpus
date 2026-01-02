from typing import Dict, Any
import io
from mutagen import File as MutagenFile

from .interface import DocumentExtractorInterface
from common.providers.audio_transcription.google_speech import (
    GoogleSpeechToTextProvider,
)
from common.providers.audio_transcription.openai_whisper import OpenAIWhisperProvider
from common.providers.audio_transcription.constants import AudioFormat
from common.providers.storage.factory import get_storage
from common.core.otel_axiom_exporter import get_logger
from packages.documents.models.domain.document import DocumentModel

logger = get_logger(__name__)


class AudioExtractor(DocumentExtractorInterface):
    """Document extractor for audio files using transcription."""

    SUPPORTED_TYPES = {
        "audio/mpeg": AudioFormat.MP3,
        "audio/mp3": AudioFormat.MP3,
        "mp3": AudioFormat.MP3,
        "audio/wav": AudioFormat.WAV,
        "wav": AudioFormat.WAV,
        "audio/flac": AudioFormat.FLAC,
        "flac": AudioFormat.FLAC,
        "audio/ogg": AudioFormat.OGG,
        "ogg": AudioFormat.OGG,
        "audio/webm": AudioFormat.WEBM,
        "webm": AudioFormat.WEBM,
        "audio/mp4": AudioFormat.M4A,
        "audio/m4a": AudioFormat.M4A,
        "m4a": AudioFormat.M4A,
        "audio/aac": AudioFormat.AAC,
        "aac": AudioFormat.AAC,
    }

    def __init__(self):
        self.google_provider = GoogleSpeechToTextProvider()
        self.whisper_provider = OpenAIWhisperProvider()
        self.storage = get_storage()

    def supports_file_type(self, file_type: str) -> bool:
        """Check if the extractor supports the given file type."""
        return file_type.lower() in self.SUPPORTED_TYPES

    async def _get_audio_duration(self, audio_data: bytes) -> float:
        """
        Get actual audio duration using mutagen library.

        Args:
            audio_data: The audio file data as bytes

        Returns:
            Duration in seconds, or -1 if unable to determine
        """
        try:
            audio_file = io.BytesIO(audio_data)
            mutagen_file = MutagenFile(audio_file)

            if (
                mutagen_file is not None
                and hasattr(mutagen_file, "info")
                and mutagen_file.info is not None
            ):
                duration = mutagen_file.info.length
                logger.debug(f"Detected audio duration: {duration:.1f} seconds")
                return duration
            else:
                logger.warning("Could not determine audio duration with mutagen")
                return -1
        except Exception as e:
            logger.warning(f"Error getting audio duration: {e}")
            return -1

    async def extract_text(self, document: DocumentModel) -> str:
        """Extract text content from an audio file via transcription."""
        try:
            file_type = document.content_type or ""
            file_type_lower = file_type.lower()

            if not self.supports_file_type(file_type_lower):
                raise ValueError(f"Unsupported audio file type: {file_type}")

            audio_format = self.SUPPORTED_TYPES[file_type_lower]

            # Check if either provider supports the format
            if not (
                self.google_provider.supports_format(audio_format)
                or self.whisper_provider.supports_format(audio_format)
            ):
                raise ValueError(
                    f"Transcription provider does not support format: {audio_format}"
                )

            logger.info(
                f"Starting transcription of {file_type} audio file: {document.storage_key}"
            )

            # Try URI-based transcription first (for GCS), fall back to bytes
            transcript = await self._transcribe_with_fallback(document, audio_format)

            logger.info(f"Audio transcription completed: {len(transcript)} characters")
            return transcript

        except Exception as e:
            logger.error(f"Error extracting text from audio {file_type}: {e}")
            raise Exception(f"Failed to extract text from audio: {str(e)}")

    async def _transcribe_with_fallback(
        self, document: DocumentModel, audio_format: AudioFormat
    ) -> str:
        """
        Smart transcription pipeline:
        1. If GCS available: Use GCS URI with appropriate Google method (short vs long)
        2. If Google fails or not GCS: Fall back to Whisper with bytes

        Args:
            document: The document model with storage information
            audio_format: The audio file format

        Returns:
            The transcribed text
        """
        # First, download the file to check duration and as fallback
        logger.info(
            "Downloading audio file to determine duration and prepare for fallback"
        )
        file_data = await self.storage.download(document.storage_key)
        if not file_data:
            raise ValueError(
                f"Failed to download audio file from {document.storage_key}"
            )

        # Get actual audio duration
        duration = await self._get_audio_duration(file_data)

        # Try Google Speech-to-Text first if we can get storage URI for GCS
        try:
            storage_uri = await self.storage.get_storage_uri(document.storage_key)

            if storage_uri.startswith("gs://") and self.google_provider.supports_format(
                audio_format
            ):
                if duration == -1:
                    logger.warning(
                        "Could not determine duration, defaulting to long_running_recognize for GCS"
                    )
                    try:
                        return await self.google_provider.transcribe_audio_uri(
                            storage_uri=storage_uri, audio_format=audio_format
                        )
                    except Exception as e:
                        logger.warning(f"GCS long_running_recognize failed: {e}")
                elif duration <= 60:
                    logger.info(
                        f"Audio duration {duration:.1f}s <= 60s, trying GCS short recognize first"
                    )
                    try:
                        # For GCS, short method still uses URI but with regular recognize
                        # We'll need to fall back to bytes method for short files
                        return await self.google_provider.transcribe_audio_bytes(
                            audio_data=file_data, audio_format=audio_format
                        )
                    except Exception as e:
                        logger.warning(
                            f"GCS short recognize failed: {e}, trying long method"
                        )
                        try:
                            return await self.google_provider.transcribe_audio_uri(
                                storage_uri=storage_uri, audio_format=audio_format
                            )
                        except Exception as e2:
                            logger.warning(
                                f"GCS long_running_recognize also failed: {e2}"
                            )
                else:
                    logger.info(
                        f"Audio duration {duration:.1f}s > 60s, using GCS long_running_recognize"
                    )
                    try:
                        return await self.google_provider.transcribe_audio_uri(
                            storage_uri=storage_uri, audio_format=audio_format
                        )
                    except Exception as e:
                        logger.warning(f"GCS long_running_recognize failed: {e}")
            else:
                logger.info(
                    f"Storage URI {storage_uri} is not GCS or Google doesn't support {audio_format}"
                )

        except Exception as e:
            logger.warning(f"Could not get storage URI or Google failed: {e}")

        # Fall back to Whisper
        if self.whisper_provider.supports_format(audio_format):
            logger.info("Falling back to OpenAI Whisper transcription")
            try:
                return await self.whisper_provider.transcribe_audio_bytes(
                    audio_data=file_data, audio_format=audio_format
                )
            except Exception as e:
                logger.error(f"Whisper transcription also failed: {e}")
                raise Exception(
                    f"All transcription methods failed. Last error: {str(e)}"
                )
        else:
            raise ValueError(
                f"No transcription provider supports format: {audio_format}"
            )

    async def get_metadata(self, document: DocumentModel) -> Dict[str, Any]:
        """Required by interface but not implemented for audio files."""
        return {
            "file_size": document.file_size or 0,
            "file_type": document.content_type or "",
        }
