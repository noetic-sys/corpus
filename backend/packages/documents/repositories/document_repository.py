from __future__ import annotations

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from common.repositories.base import BaseRepository
from packages.documents.models.database.document import ExtractionStatus
from packages.documents.models.database.document import DocumentEntity
from packages.documents.models.domain.document import (
    DocumentModel,
    DocumentExtractionStatsModel,
)
from common.core.otel_axiom_exporter import trace_span


class DocumentRepository(BaseRepository[DocumentEntity, DocumentModel]):
    def __init__(self, db_session: AsyncSession):
        super().__init__(DocumentEntity, DocumentModel, db_session)

    @trace_span
    async def get(
        self, entity_id: int, company_id: Optional[int] = None
    ) -> Optional[DocumentModel]:
        """Get document by ID with company filtering."""
        query = select(self.entity_class).where(
            self.entity_class.id == entity_id,
            self.entity_class.deleted == False,  # noqa
        )
        if company_id:
            query = self._add_company_filter(query, company_id)
        result = await self.db_session.execute(query)
        entity = result.scalar_one_or_none()
        return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def get_by_storage_key(
        self, storage_key: str, company_id: int
    ) -> Optional[DocumentModel]:
        query = select(self.entity_class).where(
            self.entity_class.storage_key == storage_key,
            self.entity_class.deleted == False,  # noqa
        )
        query = self._add_company_filter(query, company_id)
        result = await self.db_session.execute(query)
        entity = result.scalar_one_or_none()
        return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def get_valid_ids(
        self, document_ids: List[int], company_id: Optional[int] = None
    ) -> List[int]:
        """Get valid document IDs that exist and are not deleted, filtered by company."""
        valid_docs_query = select(DocumentEntity.id).where(
            DocumentEntity.id.in_(document_ids),
            DocumentEntity.deleted == False,  # noqa
        )
        if company_id:
            query = self._add_company_filter(valid_docs_query, company_id)
        result = await self.db_session.execute(valid_docs_query)
        return [row[0] for row in result.fetchall()]

    @trace_span
    async def update_extraction_status(
        self,
        document_id: int,
        extraction_status: str,
        extracted_content_path: Optional[str] = None,
    ) -> Optional[DocumentModel]:
        """Update document extraction status and optionally the extracted content path."""
        update_data = {"extraction_status": extraction_status}
        if extracted_content_path:
            update_data["extracted_content_path"] = extracted_content_path

        return await self.update(document_id, update_data)

    @trace_span
    async def get_pending_extraction_documents(
        self, company_id: int, limit: Optional[int] = None
    ) -> List[DocumentModel]:
        """Get documents with pending extraction status for a specific company."""

        query = select(self.entity_class).where(
            self.entity_class.extraction_status == ExtractionStatus.PENDING,
            self.entity_class.deleted == False,  # noqa
        )
        query = self._add_company_filter(query, company_id)

        if limit:
            query = query.limit(limit)

        result = await self.db_session.execute(query)
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    async def get_by_checksum(
        self, checksum: str, company_id: int
    ) -> Optional[DocumentModel]:
        """Get a document by its checksum within a company."""
        query = select(self.entity_class).where(
            self.entity_class.checksum == checksum,
            self.entity_class.deleted == False,  # noqa
        )
        query = self._add_company_filter(query, company_id)
        result = await self.db_session.execute(query)
        entity = result.scalar_one_or_none()
        return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def get_by_ids(
        self, entity_ids: List[int], company_id: Optional[int] = None
    ) -> List[DocumentModel]:
        """Get multiple documents by IDs with company filtering."""
        query = select(self.entity_class).where(
            self.entity_class.id.in_(entity_ids),
            self.entity_class.deleted == False,  # noqa
        )
        if company_id:
            query = self._add_company_filter(query, company_id)
        result = await self.db_session.execute(query)
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    async def delete(self, entity_id: int, company_id: int) -> bool:
        """Delete document with company access control."""
        # First verify the document belongs to the company
        document = await self.get(entity_id, company_id)
        if not document:
            return False

        # Use the base class delete method
        return await super().delete(entity_id)

    @trace_span
    async def get_extraction_stats_by_document_ids(
        self, document_ids: List[int], company_id: Optional[int] = None
    ) -> DocumentExtractionStatsModel:
        """Get extraction statistics for a list of document IDs."""
        if not document_ids:
            return DocumentExtractionStatsModel(
                total_documents=0,
                pending=0,
                processing=0,
                completed=0,
                failed=0,
            )

        query = select(
            self.entity_class.extraction_status,
            func.count(self.entity_class.id).label("count"),
        ).where(
            self.entity_class.id.in_(document_ids),
            self.entity_class.deleted == False,  # noqa
        )

        if company_id:
            query = self._add_company_filter(query, company_id)

        query = query.group_by(self.entity_class.extraction_status)

        result = await self.db_session.execute(query)

        # Build counts for each status
        counts = {
            ExtractionStatus.PENDING.value: 0,
            ExtractionStatus.PROCESSING.value: 0,
            ExtractionStatus.COMPLETED.value: 0,
            ExtractionStatus.FAILED.value: 0,
        }

        for row in result:
            status_value, count = row
            counts[status_value] = count

        total = sum(counts.values())

        return DocumentExtractionStatsModel(
            total_documents=total,
            pending=counts[ExtractionStatus.PENDING.value],
            processing=counts[ExtractionStatus.PROCESSING.value],
            completed=counts[ExtractionStatus.COMPLETED.value],
            failed=counts[ExtractionStatus.FAILED.value],
        )

    @trace_span
    async def get_failed_extraction_documents(
        self, company_id: Optional[int] = None, limit: Optional[int] = None
    ) -> List[DocumentModel]:
        """Get documents with failed extraction status."""
        query = select(self.entity_class).where(
            self.entity_class.extraction_status == ExtractionStatus.FAILED,
            self.entity_class.deleted == False,  # noqa
        )

        if company_id:
            query = self._add_company_filter(query, company_id)

        if limit:
            query = query.limit(limit)

        result = await self.db_session.execute(query)
        entities = result.scalars().all()
        return self._entities_to_domain(entities)
