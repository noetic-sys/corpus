"""Interface for vector-based semantic search."""

from abc import ABC, abstractmethod
from typing import List
from packages.documents.providers.document_search.types import (
    ChunkSearchResult,
    ChunkSearchFilters,
)


class VectorSearchInterface(ABC):
    """Interface for vector-based semantic search providers."""

    @abstractmethod
    async def index_chunk_embedding(
        self,
        chunk_id: str,
        document_id: int,
        company_id: int,
        embedding: List[float],
        metadata: dict,
    ) -> bool:
        """
        Index a chunk's vector embedding for semantic search.

        Args:
            chunk_id: Unique chunk identifier
            document_id: Parent document ID
            company_id: Company ID for filtering
            embedding: Vector embedding
            metadata: Chunk metadata for filtering (matrix_id, entity_set_id, etc.)

        Returns:
            True if indexing succeeded
        """
        pass

    @abstractmethod
    async def index_embeddings_bulk(self, embeddings: List[dict]) -> bool:
        """
        Bulk index chunk embeddings.

        Args:
            embeddings: List of dicts with keys: chunk_id, document_id, company_id, embedding, metadata

        Returns:
            True if bulk indexing succeeded
        """
        pass

    @abstractmethod
    async def vector_search_chunks(
        self,
        query_vector: List[float],
        filters: ChunkSearchFilters,
        skip: int = 0,
        limit: int = 10,
    ) -> ChunkSearchResult:
        """
        Search chunks using vector similarity (cosine, dot product, etc.).

        Args:
            query_vector: Query embedding vector
            filters: Search filters (company_id, document_ids, etc.)
            skip: Number of results to skip
            limit: Maximum number of results to return

        Returns:
            ChunkSearchResult with ranked chunks and similarity scores
        """
        pass

    @abstractmethod
    async def delete_chunk_embedding(self, chunk_id: str, document_id: int) -> bool:
        """
        Remove a chunk embedding from vector search index.

        Args:
            chunk_id: Chunk identifier
            document_id: Parent document ID

        Returns:
            True if deletion succeeded
        """
        pass

    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """
        Get the vector dimension this provider expects.

        Returns:
            Embedding dimension size
        """
        pass
