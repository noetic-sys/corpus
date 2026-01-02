"""Schemas for document chunk API responses."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChunkMetadataResponse(BaseModel):
    """Metadata for a single chunk without content."""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    section: Optional[str] = Field(None, description="Section title if available")
    page_range: Optional[str] = Field(None, description="Page range (e.g., '1-3')")
    page_start: Optional[int] = Field(None, description="Starting page number")
    page_end: Optional[int] = Field(None, description="Ending page number")
    char_start: int = Field(..., description="Character position in original document")
    char_end: int = Field(
        ..., description="Character end position in original document"
    )
    overlap_prev: bool = Field(False, description="Has overlap with previous chunk")
    overlap_next: bool = Field(False, description="Has overlap with next chunk")


class ChunkResponse(BaseModel):
    """Full chunk response with content."""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: int = Field(..., description="Parent document ID")
    content: str = Field(..., description="Chunk text content")
    metadata: ChunkMetadataResponse = Field(..., description="Chunk metadata")


class ChunkListResponse(BaseModel):
    """Response for list of chunks with manifest."""

    document_id: int = Field(..., description="Document ID")
    total_chunks: int = Field(..., description="Total number of chunks")
    chunks: List[ChunkMetadataResponse] = Field(
        ..., description="List of chunk metadata"
    )


class ChunkManifestResponse(BaseModel):
    """Complete chunk manifest for a document."""

    document_id: int = Field(..., description="Document ID")
    total_chunks: int = Field(..., description="Total number of chunks")
    created_at: str = Field(..., description="ISO timestamp of chunk creation")
    chunks: List[ChunkMetadataResponse] = Field(
        ..., description="Chunk manifest entries"
    )


# Upload schemas (for chunking agent to upload chunks)
class ChunkUploadItem(BaseModel):
    """Single chunk data for upload from chunking agent."""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Chunk text content")
    metadata: Dict[str, Any] = Field(..., description="Chunk metadata")


class ChunksUploadRequest(BaseModel):
    """Request body for uploading chunks from chunking agent."""

    document_id: int = Field(..., description="Document ID")
    company_id: int = Field(..., description="Company ID")
    chunks: List[ChunkUploadItem] = Field(..., description="List of chunks to upload")


class ChunksUploadResponse(BaseModel):
    """Response for chunk upload."""

    document_id: int = Field(..., description="Document ID")
    chunk_count: int = Field(..., description="Number of chunks uploaded")
    s3_prefix: str = Field(..., description="S3 prefix where chunks are stored")


# Hybrid search schemas
class ChunkSearchHitResponse(BaseModel):
    """Single chunk search result with score."""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: int = Field(..., description="Parent document ID")
    content: str = Field(..., description="Chunk text content")
    score: float = Field(..., description="Relevance score from hybrid search")
    metadata: Dict[str, Any] = Field(..., description="Chunk metadata")


class ChunkSearchResponse(BaseModel):
    """Response for hybrid chunk search."""

    query: str = Field(..., description="Search query text")
    total_count: int = Field(..., description="Total number of results found")
    has_more: bool = Field(..., description="Whether more results are available")
    chunks: List[ChunkSearchHitResponse] = Field(..., description="Search results")
