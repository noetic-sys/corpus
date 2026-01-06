from typing import Optional, Dict, List
from .interface import APIKeyRotationInterface
from .rotation_provider import APIKeyRotationProvider
from .provider_enum import APIProviderType
from common.core.config import settings
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)

# Global registry of provider rotators
_provider_rotators: Dict[APIProviderType, APIKeyRotationInterface] = {}


def get_rotator(provider: APIProviderType) -> Optional[APIKeyRotationInterface]:
    """
    Get the rotation provider for a specific API provider type.
    Lazily initializes rotators on first access.

    Args:
        provider: The API provider type to get rotator for

    Returns:
        The rotation provider instance, or None if not available
    """
    if provider not in _provider_rotators:
        # Lazy initialization on first access
        _initialize_single_rotator(provider)

    return _provider_rotators.get(provider)


def _initialize_single_rotator(provider: APIProviderType) -> None:
    """Initialize a single provider's rotator if keys are available."""
    keys = _get_keys_for_provider(provider)
    if keys:
        _provider_rotators[provider] = APIKeyRotationProvider(
            keys=keys, provider_type=provider
        )
        logger.info(f"Initialized {provider.value} rotator with {len(keys)} keys")


def _get_keys_for_provider(provider: APIProviderType) -> Optional[List[str]]:
    """Get API keys for a specific provider from settings."""
    match provider:
        case APIProviderType.OPENAI:
            return settings.openai_api_keys
        case APIProviderType.GEMINI:
            return settings.gemini_api_keys
        case APIProviderType.VOYAGE:
            return settings.voyage_api_keys
        case _:
            return None


def initialize_all_rotators() -> None:
    """
    Initialize all available rotators at once.
    Useful for startup/warmup scenarios.
    """
    for provider in APIProviderType:
        if provider not in _provider_rotators:
            _initialize_single_rotator(provider)

    logger.info(f"Initialized {len(_provider_rotators)} API key rotators total")


def reset_rotators() -> None:
    """Reset all rotators. Useful for testing."""
    global _provider_rotators
    _provider_rotators.clear()
    logger.info("Cleared all API key rotators")
