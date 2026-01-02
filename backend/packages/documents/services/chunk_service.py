"""Service for managing individual chunks."""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.documents.repositories.chunk_repository import ChunkRepository
from packages.documents.models.domain.chunk import (
    ChunkModel,
    ChunkCreateModel,
    ChunkUpdateModel,
)

logger = get_logger(__name__)


class ChunkService:
    """Service for managing individual chunks."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.chunk_repo = ChunkRepository(db_session)

    @trace_span
    async def create_chunk(self, chunk_data: ChunkCreateModel) -> ChunkModel:
        """Create a new chunk."""
        chunk = await self.chunk_repo.create(chunk_data)
        logger.info(f"Created chunk {chunk.chunk_id} for document {chunk.document_id}")
        return chunk

    @trace_span
    async def create_chunks_batch(
        self, chunks_data: List[ChunkCreateModel]
    ) -> List[ChunkModel]:
        """Create multiple chunks in batch."""
        chunks = []
        for chunk_data in chunks_data:
            chunk = await self.chunk_repo.create(chunk_data)
            chunks.append(chunk)

        logger.info(f"Created {len(chunks)} chunks")
        return chunks

    @trace_span
    async def get_chunk(
        self, chunk_id: int, company_id: Optional[int] = None
    ) -> Optional[ChunkModel]:
        """Get a chunk by ID."""
        return await self.chunk_repo.get(chunk_id, company_id)

    @trace_span
    async def get_chunk_by_chunk_id(
        self, chunk_id: str, document_id: int, company_id: Optional[int] = None
    ) -> Optional[ChunkModel]:
        """Get a chunk by its chunk_id and document_id."""
        return await self.chunk_repo.get_by_chunk_id(chunk_id, document_id, company_id)

    @trace_span
    async def get_chunks_for_chunk_set(
        self, chunk_set_id: int, company_id: Optional[int] = None
    ) -> List[ChunkModel]:
        """Get all chunks for a chunk set."""
        return await self.chunk_repo.get_by_chunk_set_id(chunk_set_id, company_id)

    @trace_span
    async def get_chunks_for_document(
        self, document_id: int, company_id: Optional[int] = None
    ) -> List[ChunkModel]:
        """Get all chunks for a document."""
        return await self.chunk_repo.get_by_document_id(document_id, company_id)

    @trace_span
    async def update_chunk(
        self,
        chunk_id: int,
        company_id: int,
        update_data: ChunkUpdateModel,
    ) -> Optional[ChunkModel]:
        """Update a chunk."""
        chunk = await self.chunk_repo.update(chunk_id, company_id, update_data)
        if chunk:
            logger.info(f"Updated chunk {chunk_id}")
        return chunk

    @trace_span
    async def delete_chunk(self, chunk_id: int, company_id: int) -> bool:
        """Soft delete a chunk."""
        success = await self.chunk_repo.delete(chunk_id, company_id)
        if success:
            logger.info(f"Deleted chunk {chunk_id}")
        return success
