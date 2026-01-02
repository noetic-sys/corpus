from typing import Optional
from .interface import AIProviderInterface
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .google_provider import GoogleProvider
from .xai_provider import XAIProvider
from .provider_enum import AIProviderType
from common.core.config import settings


def get_ai_provider(
    provider_type: Optional[str] = None,
    model_name: Optional[str] = None,
) -> AIProviderInterface:
    """
    Get AI provider instance.

    Args:
        provider_type: Type of provider ('openai', 'anthropic').
                      If None, uses the default from settings.
        model_name: Specific model to use. If None, uses provider default.

    Returns:
        An instance of the requested AI provider.
    """
    if provider_type is None:
        provider_type = settings.default_ai_provider

    provider_type = provider_type.lower()

    match provider_type:
        case AIProviderType.OPENAI:
            return OpenAIProvider(model_name=model_name)
        case AIProviderType.ANTHROPIC:
            return AnthropicProvider(model_name=model_name)
        case AIProviderType.GOOGLE:
            return GoogleProvider(model_name=model_name)
        case AIProviderType.XAI:
            return XAIProvider(model_name=model_name)
        case _:
            raise ValueError(f"Unknown AI provider type: {provider_type}")
