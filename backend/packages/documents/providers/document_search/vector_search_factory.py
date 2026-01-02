"""Factory for creating vector search provider instances."""

from typing import Optional

from packages.documents.providers.document_search.vector_search_interface import (
    VectorSearchInterface,
)
from packages.documents.providers.document_search.elasticsearch_vector_search import (
    ElasticsearchVectorSearch,
)
from packages.documents.providers.document_search.types import VectorSearchProvider
from common.core.config import settings


def get_vector_search_provider(
    provider_type: Optional[str] = None,
    elasticsearch_url: Optional[str] = None,
    embedding_dim: int = 1536,
) -> VectorSearchInterface:
    """
    Get vector search provider instance.

    Args:
        provider_type: Type of provider ('elasticsearch').
                      If None, defaults to elasticsearch.
        elasticsearch_url: Elasticsearch URL (if using elasticsearch provider)
        embedding_dim: Embedding dimension size

    Returns:
        An instance of the requested vector search provider.

    Raises:
        ValueError: If provider type is unknown.
    """
    if provider_type is None:
        provider_type = "elasticsearch"

    provider_type = provider_type.lower()

    match provider_type:
        case VectorSearchProvider.ELASTICSEARCH:
            es_url = (
                elasticsearch_url if elasticsearch_url else settings.elasticsearch_url
            )
            return ElasticsearchVectorSearch(
                elasticsearch_url=es_url, embedding_dim=embedding_dim
            )
        case _:
            raise ValueError(f"Unknown vector search provider type: {provider_type}")
