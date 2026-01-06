from typing import Optional

from .interface import AIProviderInterface
from .openrouter_provider import OpenRouterProvider
from common.core.config import settings


def get_ai_provider(
    model_name: Optional[str] = None,
) -> AIProviderInterface:
    """
    Get AI provider instance via OpenRouter.

    Args:
        model_name: Model in OpenRouter format (e.g., 'anthropic/claude-3.5-sonnet').
                   If None, uses the default from settings.

    Returns:
        An instance of OpenRouterProvider configured with the specified model.
    """
    model = model_name or settings.default_model
    return OpenRouterProvider(model_name=model)
