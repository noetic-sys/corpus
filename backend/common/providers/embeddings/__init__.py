"""Embedding providers for generating vector embeddings."""

from common.providers.embeddings.factory import get_embedding_provider
from common.providers.embeddings.interface import EmbeddingProviderInterface

__all__ = ["get_embedding_provider", "EmbeddingProviderInterface"]
