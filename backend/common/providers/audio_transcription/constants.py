from enum import Enum


class AudioFormat(Enum):
    """Supported audio formats for transcription."""

    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"
    OGG = "ogg"
    WEBM = "webm"
    M4A = "m4a"
    AAC = "aac"
