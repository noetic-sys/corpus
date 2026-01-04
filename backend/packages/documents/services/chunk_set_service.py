"""Service for managing chunk sets."""

from typing import List, Optional

from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.documents.repositories.chunk_set_repository import ChunkSetRepository
from packages.documents.models.domain.chunk_set import (
    ChunkSetModel,
    ChunkSetCreateModel,
    ChunkSetUpdateModel,
)

logger = get_logger(__name__)


class ChunkSetService:
    """Service for managing chunk sets."""

    def __init__(self):
        self.chunk_set_repo = ChunkSetRepository()

    @trace_span
    async def create_chunk_set(
        self, chunk_set_data: ChunkSetCreateModel
    ) -> ChunkSetModel:
        """Create a new chunk set."""
        chunk_set = await self.chunk_set_repo.create(chunk_set_data)
        logger.info(
            f"Created chunk set {chunk_set.id} for document {chunk_set.document_id}"
        )
        return chunk_set

    @trace_span
    async def get_chunk_set(
        self, chunk_set_id: int, company_id: Optional[int] = None
    ) -> Optional[ChunkSetModel]:
        """Get a chunk set by ID."""
        return await self.chunk_set_repo.get(chunk_set_id, company_id)

    @trace_span
    async def get_chunk_sets_for_document(
        self, document_id: int, company_id: Optional[int] = None
    ) -> List[ChunkSetModel]:
        """Get all chunk sets for a document."""
        return await self.chunk_set_repo.get_by_document_id(document_id, company_id)

    @trace_span
    async def get_current_chunk_set(
        self, document_id: int, company_id: Optional[int] = None
    ) -> Optional[ChunkSetModel]:
        """Get the current/latest chunk set for a document."""
        return await self.chunk_set_repo.get_current_for_document(
            document_id, company_id
        )

    @trace_span
    async def update_chunk_set(
        self,
        chunk_set_id: int,
        company_id: int,
        update_data: ChunkSetUpdateModel,
    ) -> Optional[ChunkSetModel]:
        """Update a chunk set."""
        chunk_set = await self.chunk_set_repo.update(
            chunk_set_id, company_id, update_data
        )
        if chunk_set:
            logger.info(f"Updated chunk set {chunk_set_id}")
        return chunk_set

    @trace_span
    async def delete_chunk_set(self, chunk_set_id: int, company_id: int) -> bool:
        """Soft delete a chunk set."""
        success = await self.chunk_set_repo.delete(chunk_set_id, company_id)
        if success:
            logger.info(f"Deleted chunk set {chunk_set_id}")
        return success
