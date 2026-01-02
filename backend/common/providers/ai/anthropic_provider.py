from typing import Optional, Dict, Any

from common.core.config import settings
from .provider_enum import AIProviderType
from .aisuite_provider import AISuiteProvider
from common.providers.api_keys.rotation_provider import APIKeyRotationProvider
from common.providers.api_keys.provider_enum import (
    APIProviderType as KeyAPIProviderType,
)


class AnthropicProvider(AISuiteProvider):
    """Anthropic (Claude) implementation using aisuite unified interface."""

    def __init__(self, model_name: Optional[str] = None):
        model = model_name or settings.anthropic_model

        # Create our own rotator with anthropic keys
        rotator = APIKeyRotationProvider(
            keys=settings.anthropic_api_keys, provider_type=KeyAPIProviderType.ANTHROPIC
        )

        super().__init__(
            provider=AIProviderType.ANTHROPIC.value, model_name=model, rotator=rotator
        )

    def get_config_dict(self, rotated_key: str) -> Dict[str, Any]:
        """Get Anthropic-specific configuration dictionary with rotated key."""
        return {"api_key": rotated_key}
