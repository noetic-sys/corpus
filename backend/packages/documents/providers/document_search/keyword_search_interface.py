"""Interface for keyword-based search (BM25, full-text, etc.)"""

from abc import ABC, abstractmethod
from typing import List
from packages.documents.providers.document_search.types import (
    ChunkSearchResult,
    ChunkSearchFilters,
)


class KeywordSearchInterface(ABC):
    """Interface for keyword-based chunk search providers (BM25, full-text)."""

    @abstractmethod
    async def index_chunk(
        self,
        chunk_id: str,
        document_id: int,
        company_id: int,
        content: str,
        metadata: dict,
    ) -> bool:
        """
        Index a chunk for keyword search.

        Args:
            chunk_id: Unique chunk identifier
            document_id: Parent document ID
            company_id: Company ID for filtering
            content: Chunk text content
            metadata: Chunk metadata (section, page, etc.)

        Returns:
            True if indexing succeeded
        """
        pass

    @abstractmethod
    async def index_chunks_bulk(self, chunks: List[dict]) -> bool:
        """
        Bulk index chunks for keyword search.

        Args:
            chunks: List of chunk dicts with keys: chunk_id, document_id, company_id, content, metadata

        Returns:
            True if bulk indexing succeeded
        """
        pass

    @abstractmethod
    async def keyword_search_chunks(
        self,
        query: str,
        filters: ChunkSearchFilters,
        skip: int = 0,
        limit: int = 10,
    ) -> ChunkSearchResult:
        """
        Search chunks using keyword matching (BM25, full-text).

        Args:
            query: Search query text
            filters: Search filters (company_id, document_ids, etc.)
            skip: Number of results to skip
            limit: Maximum number of results to return

        Returns:
            ChunkSearchResult with ranked chunks and BM25 scores
        """
        pass

    @abstractmethod
    async def delete_chunk_from_index(self, chunk_id: str, document_id: int) -> bool:
        """
        Remove a chunk from keyword search index.

        Args:
            chunk_id: Chunk identifier
            document_id: Parent document ID

        Returns:
            True if deletion succeeded
        """
        pass
