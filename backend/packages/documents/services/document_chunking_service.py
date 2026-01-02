"""
Service for retrieving document chunks with content from S3.

This service bridges the gap between database chunk metadata and S3 content storage.
It uses ChunkService to get metadata from DB and loads content from S3.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from common.providers.storage.factory import get_storage
from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.documents.services.chunk_service import ChunkService
from packages.documents.services.chunk_set_service import ChunkSetService

# Use the libs/documents chunk model for agent-facing API
from documents.chunk import DocumentChunk

logger = get_logger(__name__)


class DocumentChunkingService:
    """Service for retrieving document chunks with content."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.storage = get_storage()
        self.chunk_service = ChunkService(db_session)
        self.chunk_set_service = ChunkSetService(db_session)

    @trace_span
    async def get_chunks_for_document(
        self, document_id: int, company_id: int
    ) -> List[DocumentChunk]:
        """
        Get all chunks for a document with content from S3.

        Args:
            document_id: Document ID
            company_id: Company ID for authorization

        Returns:
            List of DocumentChunk objects with content loaded from S3
        """
        # Get chunks from database
        chunk_models = await self.chunk_service.get_chunks_for_document(
            document_id, company_id
        )

        if not chunk_models:
            logger.info(f"No chunks found in database for document {document_id}")
            return []

        # Load content from S3 for each chunk
        chunks_with_content = []
        for chunk_model in chunk_models:
            try:
                # Download content from S3
                content_bytes = await self.storage.download(chunk_model.s3_key)
                if content_bytes:
                    content = content_bytes.decode("utf-8")
                else:
                    logger.warning(
                        f"No content found in S3 for chunk {chunk_model.chunk_id}"
                    )
                    content = ""

                # Create DocumentChunk with content
                chunk_with_content = DocumentChunk(
                    chunk_id=chunk_model.chunk_id,
                    document_id=chunk_model.document_id,
                    content=content,
                    metadata=chunk_model.chunk_metadata,
                )
                chunks_with_content.append(chunk_with_content)

            except Exception as e:
                logger.error(
                    f"Failed to load content for chunk {chunk_model.chunk_id}: {e}"
                )
                # Continue with other chunks even if one fails
                continue

        logger.info(
            f"Loaded {len(chunks_with_content)} chunks with content for document {document_id}"
        )

        return chunks_with_content

    @trace_span
    async def get_chunk_by_id(
        self, chunk_id: str, document_id: int, company_id: int
    ) -> Optional[DocumentChunk]:
        """
        Get a specific chunk by ID with content from S3.

        Args:
            chunk_id: Chunk ID
            document_id: Document ID
            company_id: Company ID for authorization

        Returns:
            DocumentChunk with content, or None if not found
        """
        # Get chunk from database
        chunk_model = await self.chunk_service.get_chunk_by_chunk_id(
            chunk_id, document_id, company_id
        )

        if not chunk_model:
            return None

        # Download content from S3
        content_bytes = await self.storage.download(chunk_model.s3_key)
        if content_bytes:
            content = content_bytes.decode("utf-8")
        else:
            logger.warning(f"No content found in S3 for chunk {chunk_id}")
            content = ""

        # Create DocumentChunk with content
        return DocumentChunk(
            chunk_id=chunk_model.chunk_id,
            document_id=chunk_model.document_id,
            content=content,
            metadata=chunk_model.chunk_metadata,
        )


def get_document_chunking_service(db_session: AsyncSession) -> DocumentChunkingService:
    """Get document chunking service instance."""
    return DocumentChunkingService(db_session)
