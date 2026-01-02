"""Factory for creating keyword search provider instances."""

from typing import Optional

from packages.documents.providers.document_search.keyword_search_interface import (
    KeywordSearchInterface,
)
from packages.documents.providers.document_search.elasticsearch_keyword_search import (
    ElasticsearchKeywordSearch,
)
from packages.documents.providers.document_search.types import KeywordSearchProvider
from common.core.config import settings


def get_keyword_search_provider(
    provider_type: Optional[str] = None,
    elasticsearch_url: Optional[str] = None,
) -> KeywordSearchInterface:
    """
    Get keyword search provider instance.

    Args:
        provider_type: Type of provider ('elasticsearch', 'postgres').
                      If None, defaults to elasticsearch.
        elasticsearch_url: Elasticsearch URL (if using elasticsearch provider)

    Returns:
        An instance of the requested keyword search provider.

    Raises:
        ValueError: If provider type is unknown.
    """
    if provider_type is None:
        provider_type = "elasticsearch"

    provider_type = provider_type.lower()

    match provider_type:
        case KeywordSearchProvider.ELASTICSEARCH:
            es_url = (
                elasticsearch_url if elasticsearch_url else settings.elasticsearch_url
            )
            return ElasticsearchKeywordSearch(elasticsearch_url=es_url)
        case KeywordSearchProvider.POSTGRES:
            # TODO: Implement PostgresKeywordSearch when needed
            raise NotImplementedError("Postgres keyword search not yet implemented")
        case _:
            raise ValueError(f"Unknown keyword search provider type: {provider_type}")
