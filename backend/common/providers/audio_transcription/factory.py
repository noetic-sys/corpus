from .interface import AudioTranscriptionInterface
from .google_speech import GoogleSpeechToTextProvider


def get_audio_transcription_provider() -> AudioTranscriptionInterface:
    """
    Get an audio transcription provider.

    Returns:
        AudioTranscriptionInterface: The provider instance
    """
    return GoogleSpeechToTextProvider()
