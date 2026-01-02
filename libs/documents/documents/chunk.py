"""Domain models for document chunks."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """Represents a single document chunk with metadata.

    Chunks are semantic segments of documents stored on filesystem
    for agent-based retrieval. Each chunk maintains metadata about
    its position in the original document.
    """

    chunk_id: str = Field(description="Unique chunk identifier (e.g., 'chunk_001')")
    document_id: int = Field(description="ID of the parent document")
    content: str = Field(description="Chunk text content")
    metadata: Dict[str, Any] = Field(
        description="Chunk metadata including position, section, overlap"
    )

    @property
    def page_start(self) -> Optional[int]:
        """Starting page number in original document."""
        return self.metadata.get("page_start")

    @property
    def page_end(self) -> Optional[int]:
        """Ending page number in original document."""
        return self.metadata.get("page_end")

    @property
    def section(self) -> Optional[str]:
        """Section title or heading."""
        return self.metadata.get("section")

    @property
    def char_start(self) -> Optional[int]:
        """Character position start in original document."""
        return self.metadata.get("char_start")

    @property
    def char_end(self) -> Optional[int]:
        """Character position end in original document."""
        return self.metadata.get("char_end")

    @property
    def has_overlap_prev(self) -> bool:
        """Whether this chunk overlaps with previous chunk."""
        return self.metadata.get("overlap_prev", False)

    @property
    def has_overlap_next(self) -> bool:
        """Whether this chunk overlaps with next chunk."""
        return self.metadata.get("overlap_next", False)


class ChunkInfo(BaseModel):
    """Summary information about a chunk for manifest."""

    chunk_id: str = Field(description="Chunk identifier")
    section: Optional[str] = Field(default=None, description="Section title")
    page_range: Optional[str] = Field(
        default=None, description="Page range (e.g., '1-3')"
    )


class ChunkManifest(BaseModel):
    """Manifest describing all chunks for a document.

    Stored as manifest.json in the document's chunk directory.
    """

    document_id: int = Field(description="ID of the document")
    total_chunks: int = Field(description="Total number of chunks")
    chunks: list[ChunkInfo] = Field(description="Summary info for each chunk")
