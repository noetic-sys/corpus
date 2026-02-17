from .interface import DocumentSearchInterface
from .postgres_search import PostgresDocumentSearch
from .elasticsearch_search import ElasticsearchDocumentSearch
from .turbopuffer_document_search import TurbopufferDocumentSearch
from .types import DocumentSearchProvider
from common.core.config import settings


def get_document_search_provider() -> DocumentSearchInterface:
    """Get document search provider instance based on configuration."""
    provider_type = DocumentSearchProvider(settings.document_search_provider)

    if provider_type == DocumentSearchProvider.POSTGRES:
        return PostgresDocumentSearch()
    elif provider_type == DocumentSearchProvider.ELASTICSEARCH:
        return ElasticsearchDocumentSearch(settings.elasticsearch_url)
    elif provider_type == DocumentSearchProvider.TURBOPUFFER:
        return TurbopufferDocumentSearch(api_key=settings.turbopuffer_api_key)
    else:
        # Default to postgres if unknown provider
        return PostgresDocumentSearch()
