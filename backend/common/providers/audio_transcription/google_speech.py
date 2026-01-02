import asyncio
from typing import Optional
from google.cloud import speech
from google.api_core import exceptions as google_exceptions

from .interface import AudioTranscriptionInterface
from .constants import AudioFormat
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


class GoogleSpeechToTextProvider(AudioTranscriptionInterface):
    """Google Cloud Speech-to-Text transcription provider."""

    SUPPORTED_FORMATS = {
        AudioFormat.MP3: speech.RecognitionConfig.AudioEncoding.MP3,
        AudioFormat.WAV: speech.RecognitionConfig.AudioEncoding.LINEAR16,
        AudioFormat.FLAC: speech.RecognitionConfig.AudioEncoding.FLAC,
        AudioFormat.OGG: speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
        AudioFormat.WEBM: speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
    }

    def __init__(self):
        self.client = speech.SpeechClient()

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
        Transcribe audio data using Google Speech-to-Text.

        Args:
            audio_data: The audio file data as bytes
            audio_format: The audio file format
            language: Optional language code (defaults to 'en-US')

        Returns:
            The transcribed text as a string
        """
        try:
            if not self.supports_format(audio_format):
                raise ValueError(f"Unsupported audio format: {audio_format}")

            encoding = self.SUPPORTED_FORMATS[audio_format]
            config = speech.RecognitionConfig(
                encoding=encoding,
                sample_rate_hertz=16000,
                language_code=language or "en-US",
                enable_automatic_punctuation=True,
                model="latest_long",
            )

            audio = speech.RecognitionAudio(content=audio_data)

            logger.info(
                f"Starting Google Speech-to-Text transcription for {audio_format.value} audio"
            )

            # For longer audio files, we need to use long_running_recognize
            # The recognize method has a 1-minute limit
            audio_duration_estimate = len(audio_data) / (
                16000 * 2
            )  # Rough estimate for 16kHz, 16-bit audio

            if audio_duration_estimate > 60:  # If estimated duration > 1 minute
                logger.info(
                    f"Audio file estimated duration: {audio_duration_estimate:.1f}s, using long_running_recognize"
                )
                # Use long running recognize for longer files
                operation = await asyncio.to_thread(
                    self.client.long_running_recognize, config=config, audio=audio
                )
                response = await asyncio.to_thread(
                    operation.result, timeout=600
                )  # 10 minute timeout
            else:
                logger.info(
                    f"Audio file estimated duration: {audio_duration_estimate:.1f}s, using recognize"
                )
                # Run synchronous Google API call in thread pool to avoid blocking event loop
                response = await asyncio.to_thread(
                    self.client.recognize, config=config, audio=audio
                )

            transcript_parts = []
            for result in response.results:
                if result.alternatives:
                    transcript_parts.append(result.alternatives[0].transcript)

            full_transcript = " ".join(transcript_parts)

            logger.info(
                f"Google Speech-to-Text transcription completed: {len(full_transcript)} characters"
            )
            return full_transcript.strip()

        except google_exceptions.GoogleAPIError as e:
            logger.error(f"Google Speech-to-Text API error: {e}")
            raise Exception(f"Google Speech-to-Text transcription failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error in Google Speech-to-Text transcription: {e}")
            raise Exception(f"Failed to transcribe audio: {str(e)}")

    async def transcribe_audio_uri(
        self,
        storage_uri: str,
        audio_format: AudioFormat,
        language: Optional[str] = None,
    ) -> str:
        """
        Transcribe audio data from storage URI using Google Speech-to-Text.

        Args:
            storage_uri: The storage URI (e.g., 'gs://bucket/file')
            audio_format: The audio file format
            language: Optional language code (defaults to 'en-US')

        Returns:
            The transcribed text as a string
        """
        try:
            if not self.supports_format(audio_format):
                raise ValueError(f"Unsupported audio format: {audio_format}")

            # Only support GCS URIs for now
            if not storage_uri.startswith("gs://"):
                raise ValueError(
                    f"Google Speech-to-Text only supports GCS URIs (gs://), got: {storage_uri}"
                )

            encoding = self.SUPPORTED_FORMATS[audio_format]
            config = speech.RecognitionConfig(
                encoding=encoding,
                sample_rate_hertz=16000,
                language_code=language or "en-US",
                enable_automatic_punctuation=True,
                model="latest_long",
            )

            audio = speech.RecognitionAudio(uri=storage_uri)

            logger.info(
                f"Starting Google Speech-to-Text transcription for {audio_format.value} audio from URI: {storage_uri}"
            )

            # For URI-based transcription, always use long_running_recognize
            operation = await asyncio.to_thread(
                self.client.long_running_recognize, config=config, audio=audio
            )
            response = await asyncio.to_thread(
                operation.result, timeout=600
            )  # 10 minute timeout

            transcript_parts = []
            for result in response.results:
                if result.alternatives:
                    transcript_parts.append(result.alternatives[0].transcript)

            full_transcript = " ".join(transcript_parts)

            logger.info(
                f"Google Speech-to-Text URI transcription completed: {len(full_transcript)} characters"
            )
            return full_transcript.strip()

        except google_exceptions.GoogleAPIError as e:
            logger.error(f"Google Speech-to-Text API error: {e}")
            raise Exception(f"Google Speech-to-Text transcription failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error in Google Speech-to-Text URI transcription: {e}")
            raise Exception(f"Failed to transcribe audio from URI: {str(e)}")
