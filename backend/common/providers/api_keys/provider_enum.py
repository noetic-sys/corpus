from enum import Enum


class APIProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"  # For direct Gemini API (document extraction)
    GOOGLE = "google"  # For Vertex AI / aisuite
    XAI = "xai"
    VOYAGE = "voyage"
