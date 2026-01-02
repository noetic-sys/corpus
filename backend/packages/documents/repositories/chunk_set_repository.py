from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from common.core.otel_axiom_exporter import trace_span
from common.repositories.base import BaseRepository
from packages.documents.models.database.chunk_set import ChunkSetEntity
from packages.documents.models.domain.chunk_set import ChunkSetModel


class ChunkSetRepository(BaseRepository[ChunkSetEntity, ChunkSetModel]):
    def __init__(self, db_session: AsyncSession):
        super().__init__(ChunkSetEntity, ChunkSetModel, db_session)

    @trace_span
    async def get_by_document_id(
        self, document_id: int, company_id: Optional[int] = None
    ) -> List[ChunkSetModel]:
        """Get all chunk sets for a document."""
        query = select(ChunkSetEntity).where(
            ChunkSetEntity.document_id == document_id,
            ChunkSetEntity.deleted == False,
        )
        if company_id is not None:
            query = self._add_company_filter(query, company_id)
        result = await self.db_session.execute(query)
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    async def get_current_for_document(
        self, document_id: int, company_id: Optional[int] = None
    ) -> Optional[ChunkSetModel]:
        """Get the most recent chunk set for a document."""
        query = (
            select(ChunkSetEntity)
            .where(
                ChunkSetEntity.document_id == document_id,
                ChunkSetEntity.deleted == False,
            )
            .order_by(ChunkSetEntity.created_at.desc())
            .limit(1)
        )
        if company_id is not None:
            query = self._add_company_filter(query, company_id)
        result = await self.db_session.execute(query)
        entity = result.scalar_one_or_none()
        return self._entity_to_domain(entity) if entity else None
