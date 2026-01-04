from typing import List, Optional
from sqlalchemy.future import select
from common.core.otel_axiom_exporter import trace_span
from common.repositories.base import BaseRepository
from packages.documents.models.database.chunk import ChunkEntity
from packages.documents.models.domain.chunk import ChunkModel


class ChunkRepository(BaseRepository[ChunkEntity, ChunkModel]):
    def __init__(self):
        super().__init__(ChunkEntity, ChunkModel)

    @trace_span
    async def get_by_chunk_set_id(
        self, chunk_set_id: int, company_id: Optional[int] = None
    ) -> List[ChunkModel]:
        """Get all chunks for a chunk set."""
        async with self._get_session() as session:
            query = (
                select(ChunkEntity)
                .where(
                    ChunkEntity.chunk_set_id == chunk_set_id,
                    ChunkEntity.deleted == False,
                )
                .order_by(ChunkEntity.chunk_order)
            )
            if company_id is not None:
                query = self._add_company_filter(query, company_id)
            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def get_by_document_id(
        self, document_id: int, company_id: Optional[int] = None
    ) -> List[ChunkModel]:
        """Get all chunks for a document (denormalized query)."""
        async with self._get_session() as session:
            query = (
                select(ChunkEntity)
                .where(
                    ChunkEntity.document_id == document_id,
                    ChunkEntity.deleted == False,
                )
                .order_by(ChunkEntity.chunk_order)
            )
            if company_id is not None:
                query = self._add_company_filter(query, company_id)
            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def get_by_chunk_id(
        self, chunk_id: str, document_id: int, company_id: Optional[int] = None
    ) -> Optional[ChunkModel]:
        """Get a specific chunk by chunk_id and document_id."""
        async with self._get_session() as session:
            query = select(ChunkEntity).where(
                ChunkEntity.chunk_id == chunk_id,
                ChunkEntity.document_id == document_id,
                ChunkEntity.deleted == False,
            )
            if company_id is not None:
                query = query.where(ChunkEntity.company_id == company_id)
            result = await session.execute(query)
            entity = result.scalar_one_or_none()
            return self._entity_to_domain(entity) if entity else None
