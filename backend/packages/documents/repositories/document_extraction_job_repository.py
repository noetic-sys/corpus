from __future__ import annotations

from typing import List
from sqlalchemy.future import select
from sqlalchemy import and_

from common.repositories.base import BaseRepository
from packages.documents.models.database.document_extraction_job import (
    DocumentExtractionJobEntity,
)
from packages.documents.models.domain.document_extraction_job import (
    DocumentExtractionJobModel,
    DocumentExtractionJobStatus,
)
from packages.documents.models.database.document import DocumentEntity, ExtractionStatus
from packages.documents.models.domain.document import DocumentModel
from common.core.otel_axiom_exporter import trace_span


class DocumentExtractionJobRepository(
    BaseRepository[DocumentExtractionJobEntity, DocumentExtractionJobModel]
):
    def __init__(self):
        super().__init__(DocumentExtractionJobEntity, DocumentExtractionJobModel)

    @trace_span
    async def get_by_document_id(
        self, document_id: int
    ) -> List[DocumentExtractionJobModel]:
        """Get all extraction jobs for a document."""
        async with self._get_session() as session:
            result = await session.execute(
                select(self.entity_class)
                .where(self.entity_class.document_id == document_id)
                .order_by(self.entity_class.id.desc())
            )
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def get_pending_documents(self) -> List[DocumentModel]:
        """Get all documents with PENDING extraction status."""
        async with self._get_session() as session:
            result = await session.execute(
                select(DocumentEntity).where(
                    and_(
                        DocumentEntity.extraction_status
                        == ExtractionStatus.PENDING.value,
                        DocumentEntity.deleted == False,  # noqa
                    )
                )
            )
            entities = result.scalars().all()
            # Convert entities to domain models
            return [DocumentModel.model_validate(entity) for entity in entities]

    @trace_span
    async def get_failed_jobs(
        self, limit: int = 100
    ) -> List[DocumentExtractionJobModel]:
        """Get failed extraction jobs."""
        async with self._get_session() as session:
            result = await session.execute(
                select(self.entity_class)
                .where(
                    self.entity_class.status == DocumentExtractionJobStatus.FAILED.value
                )
                .order_by(self.entity_class.id.desc())
                .limit(limit)
            )
            entities = result.scalars().all()
            return self._entities_to_domain(entities)
