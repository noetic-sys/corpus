from typing import Optional, Dict, Any

from common.core.config import settings
from .provider_enum import AIProviderType
from .aisuite_provider import AISuiteProvider
from common.providers.api_keys.rotation_provider import APIKeyRotationProvider
from common.providers.api_keys.provider_enum import (
    APIProviderType as KeyAPIProviderType,
)


class OpenAIProvider(AISuiteProvider):
    """OpenAI implementation using aisuite unified interface."""

    def __init__(self, model_name: Optional[str] = None):
        model = model_name or getattr(settings, "openai_model", "gpt-4o-mini")

        # Create our own rotator with openai keys
        rotator = APIKeyRotationProvider(
            keys=settings.openai_api_keys, provider_type=KeyAPIProviderType.OPENAI
        )

        super().__init__(
            provider=AIProviderType.OPENAI.value, model_name=model, rotator=rotator
        )

    def get_config_dict(self, rotated_key: str) -> Dict[str, Any]:
        """Get OpenAI-specific configuration dictionary with rotated key."""
        return {"api_key": rotated_key}
