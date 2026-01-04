"""Temporal activities for indexing document chunks for search."""

from temporalio import activity
from pydantic import BaseModel

from packages.documents.services.chunk_search_service import get_chunk_search_service
from packages.documents.services.document_chunking_service import (
    get_document_chunking_service,
)
from packages.documents.models.domain.chunk_indexing import ChunkIndexingModel
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


class IndexChunksResult(BaseModel):
    """Result of chunk indexing operation."""

    success: bool
    indexed_count: int
    error: str | None = None


@activity.defn
async def index_chunks_activity(
    document_id: int,
    company_id: int,
) -> IndexChunksResult:
    """
    Index all chunks for a document for hybrid search (keyword + vector).

    Args:
        document_id: Document ID
        company_id: Company ID

    Returns:
        IndexChunksResult with indexing results
    """
    try:
        activity.logger.info(
            f"Starting chunk indexing for document {document_id}, company {company_id}"
        )

        # Get all chunks for the document
        chunking_service = get_document_chunking_service()
        chunks = await chunking_service.get_chunks_for_document(
            document_id=document_id, company_id=company_id
        )

        if not chunks:
            activity.logger.warning(f"No chunks found for document {document_id}")
            return IndexChunksResult(
                success=False,
                indexed_count=0,
                error="No chunks found",
            )

        activity.logger.info(f"Found {len(chunks)} chunks for document {document_id}")

        # Convert to indexing models
        chunk_models = [
            ChunkIndexingModel(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                company_id=company_id,
                content=c.content,
                metadata=c.metadata,
            )
            for c in chunks
        ]

        # Index chunks using search service (handles both keyword + vector)
        search_service = get_chunk_search_service()
        success = await search_service.index_chunks_bulk(chunk_models)

        if success:
            activity.logger.info(
                f"Successfully indexed {len(chunks)} chunks for document {document_id}"
            )
            return IndexChunksResult(success=True, indexed_count=len(chunks))
        else:
            activity.logger.error(f"Failed to index chunks for document {document_id}")
            return IndexChunksResult(
                success=False,
                indexed_count=0,
                error="Indexing failed",
            )

    except Exception as e:
        activity.logger.error(f"Error indexing chunks for document {document_id}: {e}")
        return IndexChunksResult(
            success=False,
            indexed_count=0,
            error=str(e),
        )
