"""
API routes for document chunk operations.

These endpoints are automatically exposed as MCP tools for workflow agents
via the workflow-agent tag.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from packages.auth.dependencies import get_current_active_user
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.documents.models.schemas.chunk import (
    ChunkListResponse,
    ChunkResponse,
    ChunkMetadataResponse,
    ChunksUploadRequest,
    ChunksUploadResponse,
    ChunkSearchResponse,
    ChunkSearchHitResponse,
)
from packages.documents.services.document_chunking_service import (
    get_document_chunking_service,
)
from packages.documents.services.document_service import get_document_service
from packages.documents.services.chunk_upload_service import get_chunk_upload_service
from packages.documents.services.chunk_search_service import get_chunk_search_service
from packages.documents.providers.document_search.types import ChunkSearchFilters
from common.core.otel_axiom_exporter import trace_span, get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/documents/{documentId}/chunks",
    response_model=ChunkListResponse,
    tags=["workflow-agent"],
    operation_id="list_document_chunks",
)
@trace_span
async def list_document_chunks(
    document_id: Annotated[int, Path(alias="documentId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """
    Get chunk metadata for a document (without content).

    Returns a list of all chunk IDs and metadata for the document,
    allowing agents to discover available chunks before reading specific ones.
    """
    # Verify document exists and user has access
    document_service = get_document_service()
    document = await document_service.get_document(document_id, current_user.company_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get chunks
    chunking_service = get_document_chunking_service()
    chunks = await chunking_service.get_chunks_for_document(
        document_id=document_id, company_id=current_user.company_id
    )

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="No chunks found for document. Document may not have been processed yet.",
        )

    # Convert to response format
    chunk_metadata_list = [ChunkMetadataResponse(**chunk.metadata) for chunk in chunks]

    return ChunkListResponse(
        document_id=document_id, total_chunks=len(chunks), chunks=chunk_metadata_list
    )


@router.get(
    "/documents/{documentId}/chunks/{chunkId}",
    response_model=ChunkResponse,
    tags=["workflow-agent"],
    operation_id="read_document_chunk",
)
@trace_span
async def read_document_chunk(
    document_id: Annotated[int, Path(alias="documentId")],
    chunk_id: Annotated[str, Path(alias="chunkId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """
    Read the full content of a specific chunk.

    Agents should use list_document_chunks first to discover available chunks,
    then read specific chunks as needed for answering questions.
    """
    # Verify document exists and user has access
    document_service = get_document_service()
    document = await document_service.get_document(document_id, current_user.company_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get all chunks for document
    chunking_service = get_document_chunking_service()
    chunks = await chunking_service.get_chunks_for_document(
        document_id=document_id, company_id=current_user.company_id
    )

    if not chunks:
        raise HTTPException(status_code=404, detail="No chunks found for document")

    # Find requested chunk
    chunk = next((c for c in chunks if c.chunk_id == chunk_id), None)
    if not chunk:
        raise HTTPException(
            status_code=404,
            detail=f"Chunk {chunk_id} not found in document {document_id}",
        )

    # Return chunk with content
    return ChunkResponse(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        content=chunk.content,
        metadata=ChunkMetadataResponse(**chunk.metadata),
    )


@router.get(
    "/documents/{documentId}/chunks/search",
    response_model=ChunkListResponse,
    tags=["workflow-agent"],
    operation_id="search_document_chunks",
)
@trace_span
async def search_document_chunks(
    document_id: Annotated[int, Path(alias="documentId")],
    section: Annotated[str | None, Query(description="Filter by section title")] = None,
    page: Annotated[int | None, Query(description="Filter by page number")] = None,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """
    Search chunks by metadata filters (section, page, etc.).

    Useful for agents to narrow down relevant chunks before reading content.
    """
    # Verify document exists and user has access
    document_service = get_document_service()
    document = await document_service.get_document(document_id, current_user.company_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get all chunks
    chunking_service = get_document_chunking_service()
    chunks = await chunking_service.get_chunks_for_document(
        document_id=document_id, company_id=current_user.company_id
    )

    if not chunks:
        raise HTTPException(status_code=404, detail="No chunks found for document")

    # Filter by metadata
    filtered_chunks = chunks
    if section:
        filtered_chunks = [
            c
            for c in filtered_chunks
            if c.metadata.get("section", "").lower() == section.lower()
        ]
    if page is not None:
        filtered_chunks = [
            c
            for c in filtered_chunks
            if (c.metadata.get("page_start") or 0)
            <= page
            <= (c.metadata.get("page_end") or 0)
        ]

    # Convert to response format
    chunk_metadata_list = [
        ChunkMetadataResponse(**chunk.metadata) for chunk in filtered_chunks
    ]

    return ChunkListResponse(
        document_id=document_id,
        total_chunks=len(filtered_chunks),
        chunks=chunk_metadata_list,
    )


@router.get(
    "/chunks/search",
    response_model=ChunkSearchResponse,
    tags=["workflow-agent"],
    operation_id="hybrid_search_chunks",
)
@trace_span
async def hybrid_search_chunks(
    query: Annotated[str, Query(description="Search query text")],
    document_ids: Annotated[
        list[int] | None, Query(description="Filter by document IDs")
    ] = None,
    matrix_id: Annotated[int | None, Query(description="Filter by matrix ID")] = None,
    entity_set_id: Annotated[
        int | None, Query(description="Filter by entity set ID")
    ] = None,
    skip: Annotated[int, Query(ge=0, description="Number of results to skip")] = 0,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Maximum results to return")
    ] = 10,
    use_vector: Annotated[
        bool, Query(description="Enable vector search (default: true)")
    ] = True,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """
    Hybrid search across chunks using BM25 + vector search.

    Combines keyword matching (BM25) with semantic similarity (vector embeddings)
    using Reciprocal Rank Fusion to rank results. Searches across all documents
    the user has access to within their company.

    Returns chunks with relevance scores, ordered by combined ranking.
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Build search filters
    filters = ChunkSearchFilters(
        company_id=current_user.company_id,
        document_ids=document_ids,
        matrix_id=matrix_id,
        entity_set_id=entity_set_id,
    )

    # Execute hybrid search
    search_service = get_chunk_search_service()
    result = await search_service.hybrid_search_chunks(
        query=query,
        filters=filters,
        skip=skip,
        limit=limit,
        use_vector=use_vector,
    )

    # Convert to response format
    chunk_hits = [
        ChunkSearchHitResponse(
            chunk_id=hit.chunk_id,
            document_id=hit.document_id,
            content=hit.content,
            score=hit.score,
            metadata=hit.metadata,
        )
        for hit in result.chunks
    ]

    return ChunkSearchResponse(
        query=query,
        total_count=result.total_count,
        has_more=result.has_more,
        chunks=chunk_hits,
    )


# Upload endpoint (called by chunking agent containers)
@router.post(
    "/documents/{documentId}/chunks",
    response_model=ChunksUploadResponse,
)
@trace_span
async def upload_document_chunks(
    document_id: Annotated[int, Path(alias="documentId")],
    upload_request: ChunksUploadRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
) -> ChunksUploadResponse:
    """
    Upload chunks from chunking agent container.

    This endpoint is called by chunking agent containers running in K8s jobs.
    The agent POSTs chunks after processing completes.
    """
    logger.info(
        f"Received chunk upload for document {document_id} from company {current_user.company_id}"
    )

    # Validate request
    if upload_request.document_id != document_id:
        raise HTTPException(
            status_code=400, detail="Document ID in path does not match request body"
        )

    if upload_request.company_id != current_user.company_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to upload chunks for this company"
        )

    # Verify document exists
    document_service = get_document_service()
    document = await document_service.get_document(document_id, current_user.company_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Process chunk upload
    chunk_upload_service = get_chunk_upload_service()
    s3_prefix = await chunk_upload_service.process_chunk_upload(
        document_id=document_id,
        company_id=current_user.company_id,
        chunks=upload_request.chunks,
    )

    logger.info(
        f"Successfully uploaded {len(upload_request.chunks)} chunks for document {document_id}"
    )

    return ChunksUploadResponse(
        document_id=document_id,
        chunk_count=len(upload_request.chunks),
        s3_prefix=s3_prefix,
    )
