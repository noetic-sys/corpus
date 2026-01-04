from typing import List, Optional
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy import func, and_

from .interface import (
    DocumentSearchInterface,
    DocumentSearchResult,
    DocumentSearchFilters,
)
from packages.documents.models.database.document import DocumentEntity
from packages.documents.models.domain.document import DocumentModel
from common.core.otel_axiom_exporter import trace_span, get_logger
from common.db.scoped import get_session

logger = get_logger(__name__)


class PostgresDocumentSearch(DocumentSearchInterface):
    """PostgreSQL-based document search implementation."""

    def __init__(self):
        pass

    def _entity_to_domain(self, entity: DocumentEntity) -> DocumentModel:
        """Convert database entity to domain model."""
        return DocumentModel.model_validate(entity)

    def _entities_to_domain(
        self, entities: List[DocumentEntity]
    ) -> List[DocumentModel]:
        """Convert list of database entities to domain models."""
        return [self._entity_to_domain(entity) for entity in entities]

    def _build_base_query(self):
        """Build base query with common filters."""
        return select(DocumentEntity).where(DocumentEntity.deleted == False)  # noqa

    def _apply_filters(self, query, filters: Optional[DocumentSearchFilters]):
        """Apply search filters to the query."""
        if not filters:
            return query

        conditions = []

        # Always filter by company_id for data federation
        conditions.append(DocumentEntity.company_id == filters.company_id)

        if filters.content_type:
            conditions.append(DocumentEntity.content_type == filters.content_type)

        if filters.extraction_status:
            conditions.append(
                DocumentEntity.extraction_status == filters.extraction_status
            )

        if filters.created_after:
            try:
                after_date = datetime.fromisoformat(filters.created_after)
                conditions.append(DocumentEntity.created_at >= after_date)
            except ValueError:
                logger.warning(
                    f"Invalid date format for created_after: {filters.created_after}"
                )

        if filters.created_before:
            try:
                before_date = datetime.fromisoformat(filters.created_before)
                conditions.append(DocumentEntity.created_at <= before_date)
            except ValueError:
                logger.warning(
                    f"Invalid date format for created_before: {filters.created_before}"
                )

        if conditions:
            query = query.where(and_(*conditions))

        return query

    def _apply_search_query(self, query, search_term: str):
        """Apply search term to the query."""
        # Search in filename using case-insensitive LIKE
        return query.where(DocumentEntity.filename.ilike(f"%{search_term}%"))

    @trace_span
    async def search_documents(
        self,
        query: Optional[str] = None,
        filters: Optional[DocumentSearchFilters] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> DocumentSearchResult:
        """Search documents with optional query and filters."""
        logger.info(
            f"Searching documents with query='{query}', skip={skip}, limit={limit}"
        )

        base_query = self._build_base_query()

        # Apply search query if provided
        if query:
            base_query = self._apply_search_query(base_query, query)

        # Apply filters
        base_query = self._apply_filters(base_query, filters)

        # Get total count (before pagination)
        count_query = select(func.count()).select_from(base_query.subquery())
        async with get_session(readonly=True) as session:
            count_result = await session.execute(count_query)
            total_count = count_result.scalar()

            # Apply pagination and ordering
            paginated_query = (
                base_query.order_by(DocumentEntity.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            # Execute query
            result = await session.execute(paginated_query)
            entities = result.scalars().all()
        documents = self._entities_to_domain(entities)

        # Determine if there are more results
        has_more = (skip + len(documents)) < total_count

        logger.info(f"Found {len(documents)} documents out of {total_count} total")

        return DocumentSearchResult(
            documents=documents, total_count=total_count, has_more=has_more
        )

    @trace_span
    async def list_documents(
        self,
        filters: Optional[DocumentSearchFilters] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> DocumentSearchResult:
        """List all documents with optional filters."""
        logger.info(f"Listing documents with skip={skip}, limit={limit}")

        # List documents is just search without a query term
        return await self.search_documents(
            query=None, filters=filters, skip=skip, limit=limit
        )

    @trace_span
    async def get_supported_filters(self) -> List[str]:
        """Get list of supported filter types."""
        return ["content_type", "extraction_status", "created_after", "created_before"]

    @trace_span
    async def health_check(self) -> bool:
        """Check if the search backend is available and healthy."""
        try:
            # Simple query to test database connectivity
            async with get_session(readonly=True) as session:
                result = await session.execute(select(1))
                result.scalar()
            return True
        except Exception as e:
            logger.error(f"PostgreSQL search health check failed: {e}")
            return False

    @trace_span
    async def index_document(
        self, document: DocumentModel, extracted_content: str = None
    ) -> bool:
        """
        Index a document for PostgreSQL search.

        For PostgreSQL, the document is already in the database,
        so this is a no-op that always returns True.
        """
        logger.debug(
            f"PostgreSQL search: Document {document.id} already indexed in database"
        )
        return True

    @trace_span
    async def delete_document_from_index(self, document_id: int) -> bool:
        """
        Remove a document from PostgreSQL search index.

        For PostgreSQL, this would typically be handled by the repository layer
        when the document is deleted from the database, so this is a no-op.
        """
        logger.debug(
            f"PostgreSQL search: Document {document_id} removal handled by database layer"
        )
        return True
