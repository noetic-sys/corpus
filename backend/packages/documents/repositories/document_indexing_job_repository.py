from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from common.core.otel_axiom_exporter import trace_span
from packages.documents.models.database.document_indexing_job import (
    DocumentIndexingJobEntity,
)
from packages.documents.models.domain.document_indexing_job import (
    DocumentIndexingJobModel,
    DocumentIndexingJobStatus,
)
from common.repositories.base import BaseRepository


class DocumentIndexingJobRepository(
    BaseRepository[DocumentIndexingJobEntity, DocumentIndexingJobModel]
):
    """Repository for document indexing job operations."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(
            DocumentIndexingJobEntity, DocumentIndexingJobModel, db_session
        )

    @trace_span
    async def get_by_document_id(
        self, document_id: int
    ) -> List[DocumentIndexingJobModel]:
        """Get all indexing jobs for a document."""
        result = await self.db_session.execute(
            select(self.entity_class)
            .where(self.entity_class.document_id == document_id)
            .order_by(self.entity_class.id.desc())
        )
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    async def get_pending_jobs(
        self, limit: int = 100
    ) -> List[DocumentIndexingJobModel]:
        """Get pending indexing jobs."""
        result = await self.db_session.execute(
            select(self.entity_class)
            .where(self.entity_class.status == DocumentIndexingJobStatus.QUEUED.value)
            .order_by(self.entity_class.id.asc())
            .limit(limit)
        )
        entities = result.scalars().all()
        return self._entities_to_domain(entities)
