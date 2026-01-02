"""Factory for creating embedding provider instances."""

from typing import Optional

from common.providers.embeddings.interface import EmbeddingProviderInterface
from common.providers.embeddings.openai_provider import OpenAIEmbeddingProvider
from common.providers.embeddings.voyage_provider import VoyageEmbeddingProvider
from common.providers.embeddings.provider_enum import EmbeddingProviderType
from common.core.config import settings


def get_embedding_provider(
    provider_type: Optional[str] = None,
    model_name: Optional[str] = None,
) -> EmbeddingProviderInterface:
    """
    Get embedding provider instance.

    Args:
        provider_type: Type of provider ('openai', 'voyage').
                      If None, uses the default from settings.
        model_name: Specific model to use. If None, uses provider default.

    Returns:
        An instance of the requested embedding provider.

    Raises:
        ValueError: If provider type is unknown.
    """
    if provider_type is None:
        provider_type = getattr(settings, "embedding_provider", "openai")

    provider_type = provider_type.lower()

    match provider_type:
        case EmbeddingProviderType.OPENAI:
            return OpenAIEmbeddingProvider(model_name=model_name)
        case EmbeddingProviderType.VOYAGE:
            return VoyageEmbeddingProvider(model_name=model_name)
        case _:
            raise ValueError(f"Unknown embedding provider type: {provider_type}")
