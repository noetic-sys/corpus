from enum import Enum


class AIProviderType(str, Enum):
    """Enumeration of supported AI provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    XAI = "xai"
