from enum import Enum


class APIProviderType(str, Enum):
    """API providers that use key rotation."""

    OPENAI = "openai"  # For embeddings and whisper
    GEMINI = "gemini"  # For document extraction
    VOYAGE = "voyage"  # For embeddings (optional)
