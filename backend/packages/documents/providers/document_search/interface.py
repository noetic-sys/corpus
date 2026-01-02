from abc import ABC, abstractmethod
from typing import List, Optional
from packages.documents.models.domain.document import DocumentModel
from packages.documents.providers.document_search.types import (
    ChunkSearchResult,
    ChunkSearchFilters,
)


class DocumentSearchResult:
    """Container for search results with metadata."""

    def __init__(
        self, documents: List[DocumentModel], total_count: int, has_more: bool
    ):
        self.documents = documents
        self.total_count = total_count
        self.has_more = has_more


class DocumentSearchFilters:
    """Search filters for document queries."""

    def __init__(
        self,
        company_id: int,
        content_type: Optional[str] = None,
        extraction_status: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
    ):
        self.company_id = company_id
        self.content_type = content_type
        self.extraction_status = extraction_status
        self.created_after = created_after
        self.created_before = created_before


class DocumentSearchInterface(ABC):
    """Interface for document search providers."""

    @abstractmethod
    async def search_documents(
        self,
        query: Optional[str] = None,
        filters: Optional[DocumentSearchFilters] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> DocumentSearchResult:
        """
        Search documents with optional query and filters.

        Args:
            query: Search term to match against document fields
            filters: Additional filters to apply
            skip: Number of results to skip (pagination)
            limit: Maximum number of results to return

        Returns:
            DocumentSearchResult containing matched documents and metadata
        """
        pass

    @abstractmethod
    async def list_documents(
        self,
        filters: Optional[DocumentSearchFilters] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> DocumentSearchResult:
        """
        List all documents with optional filters.

        Args:
            filters: Filters to apply
            skip: Number of results to skip (pagination)
            limit: Maximum number of results to return

        Returns:
            DocumentSearchResult containing documents and metadata
        """
        pass

    @abstractmethod
    async def get_supported_filters(self) -> List[str]:
        """
        Get list of supported filter types.

        Returns:
            List of supported filter field names
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the search backend is available and healthy.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abstractmethod
    async def index_document(
        self, document: DocumentModel, extracted_content: str = None
    ) -> bool:
        """
        Index a document to make it searchable.

        Args:
            document: The document to index
            extracted_content: Optional extracted text content to include in search

        Returns:
            True if indexing succeeded, False otherwise
        """
        pass

    @abstractmethod
    async def delete_document_from_index(self, document_id: int) -> bool:
        """
        Remove a document from the search index.

        Args:
            document_id: ID of the document to remove

        Returns:
            True if deletion succeeded, False otherwise
        """
        pass

    @abstractmethod
    async def index_chunk(
        self,
        chunk_id: str,
        document_id: int,
        company_id: int,
        content: str,
        metadata: dict,
        embedding: Optional[List[float]] = None,
    ) -> bool:
        """
        Index a single chunk to make it searchable.

        Args:
            chunk_id: Unique chunk identifier
            document_id: Parent document ID
            company_id: Company ID for filtering
            content: Chunk text content
            metadata: Chunk metadata (section, page, etc.)
            embedding: Optional vector embedding for semantic search

        Returns:
            True if indexing succeeded, False otherwise
        """
        pass

    @abstractmethod
    async def index_chunks_bulk(self, chunks: List[dict]) -> bool:
        """
        Bulk index multiple chunks.

        Args:
            chunks: List of chunk dicts with keys: chunk_id, document_id, company_id, content, metadata, embedding

        Returns:
            True if bulk indexing succeeded, False otherwise
        """
        pass

    @abstractmethod
    async def search_chunks(
        self,
        query: str,
        filters: ChunkSearchFilters,
        skip: int = 0,
        limit: int = 10,
    ) -> ChunkSearchResult:
        """
        Hybrid search chunks using keyword + vector similarity.
        Falls back to keyword-only if embeddings unavailable.

        Args:
            query: Search query text
            filters: Search filters (company_id, document_ids, etc.)
            skip: Number of results to skip (pagination)
            limit: Maximum number of results to return

        Returns:
            ChunkSearchResult with ranked chunks and scores
        """
        pass

    @abstractmethod
    async def delete_chunk_from_index(self, chunk_id: str, document_id: int) -> bool:
        """
        Remove a chunk from the search index.

        Args:
            chunk_id: Chunk identifier
            document_id: Parent document ID

        Returns:
            True if deletion succeeded, False otherwise
        """
        pass
