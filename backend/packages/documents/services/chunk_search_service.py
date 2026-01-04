"""Service for hybrid chunk search combining keyword + vector search."""

import asyncio
from typing import List, Optional

from packages.documents.providers.document_search.keyword_search_interface import (
    KeywordSearchInterface,
)
from packages.documents.providers.document_search.vector_search_interface import (
    VectorSearchInterface,
)
from packages.documents.providers.document_search.keyword_search_factory import (
    get_keyword_search_provider,
)
from packages.documents.providers.document_search.vector_search_factory import (
    get_vector_search_provider,
)
from packages.documents.providers.document_search.types import (
    ChunkSearchResult,
    ChunkSearchFilters,
    ChunkSearchHit,
)
from packages.documents.services.document_chunking_service import (
    get_document_chunking_service,
)
from packages.documents.models.domain.chunk_indexing import (
    ChunkIndexingModel,
    ChunkEmbeddingModel,
)
from common.providers.embeddings.factory import get_embedding_provider
from common.core.otel_axiom_exporter import get_logger, trace_span

logger = get_logger(__name__)


class ChunkSearchService:
    """Service for hybrid chunk search (keyword + vector)."""

    def __init__(
        self,
        keyword_provider: Optional[KeywordSearchInterface] = None,
        vector_provider: Optional[VectorSearchInterface] = None,
    ):
        self.keyword_provider = keyword_provider or get_keyword_search_provider()
        self.vector_provider = vector_provider or get_vector_search_provider()
        self.embedding_provider = get_embedding_provider()

    async def index_chunk(
        self,
        chunk_id: str,
        document_id: int,
        company_id: int,
        content: str,
        metadata: dict,
    ) -> bool:
        """
        Index a chunk for both keyword and vector search.

        Args:
            chunk_id: Unique chunk identifier
            document_id: Parent document ID
            company_id: Company ID
            content: Chunk text content
            metadata: Chunk metadata

        Returns:
            True if indexing succeeded
        """
        try:
            # Index for keyword search
            keyword_success = await self.keyword_provider.index_chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                company_id=company_id,
                content=content,
                metadata=metadata,
            )

            # Generate embedding and index for vector search
            vector_success = False
            try:
                embedding = await self.embedding_provider.generate_embedding(content)
                vector_success = await self.vector_provider.index_chunk_embedding(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    company_id=company_id,
                    embedding=embedding,
                    metadata=metadata,
                )
            except Exception as e:
                logger.warning(
                    f"Failed to index vector embedding for chunk {chunk_id}: {e}"
                )
                # Continue - keyword search still works

            return keyword_success  # At minimum, keyword search should succeed

        except Exception as e:
            logger.error(f"Error indexing chunk {chunk_id}: {e}")
            return False

    async def index_chunks_bulk(self, chunks: List[ChunkIndexingModel]) -> bool:
        """
        Bulk index chunks for both keyword and vector search.

        Args:
            chunks: List of ChunkIndexingModel instances

        Returns:
            True if bulk indexing succeeded
        """
        try:
            # Convert to dicts for keyword provider
            chunk_dicts = [chunk.model_dump() for chunk in chunks]
            keyword_success = await self.keyword_provider.index_chunks_bulk(chunk_dicts)

            # Generate embeddings and index for vector search
            vector_success = False
            try:
                contents = [chunk.content for chunk in chunks]
                embeddings = await self.embedding_provider.generate_embeddings(contents)

                embedding_models = [
                    ChunkEmbeddingModel(
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        company_id=chunk.company_id,
                        embedding=embedding,
                        metadata=chunk.metadata,
                    )
                    for chunk, embedding in zip(chunks, embeddings)
                ]

                # Convert to dicts for vector provider
                embedding_dicts = [emb.model_dump() for emb in embedding_models]
                vector_success = await self.vector_provider.index_embeddings_bulk(
                    embedding_dicts
                )
            except Exception as e:
                logger.warning(f"Failed to bulk index vector embeddings: {e}")
                # Continue - keyword search still works

            return keyword_success  # At minimum, keyword search should succeed

        except Exception as e:
            logger.error(f"Error bulk indexing chunks: {e}")
            return False

    @trace_span
    async def hybrid_search_chunks(
        self,
        query: str,
        filters: ChunkSearchFilters,
        skip: int = 0,
        limit: int = 10,
        use_vector: bool = True,
    ) -> ChunkSearchResult:
        """
        Hybrid search combining keyword (BM25) + vector (semantic) search.
        Gracefully falls back to keyword-only if vector search fails.

        Args:
            query: Search query text
            filters: Search filters (company_id, document_ids, etc.)
            skip: Number of results to skip
            limit: Maximum number of results to return
            use_vector: Whether to use vector search (default: True)

        Returns:
            ChunkSearchResult with ranked chunks
        """
        try:
            # Run keyword and vector search in parallel for better performance
            async def run_keyword_search():
                return await self.keyword_provider.keyword_search_chunks(
                    query=query,
                    filters=filters,
                    skip=0,  # Get more for hybrid ranking
                    limit=limit * 3,  # Retrieve more candidates
                )

            async def run_vector_search():
                if not use_vector:
                    return None
                try:
                    # Generate query embedding
                    query_embedding = await self.embedding_provider.generate_embedding(
                        query
                    )
                    filters_with_vector = ChunkSearchFilters(
                        company_id=filters.company_id,
                        document_ids=filters.document_ids,
                        matrix_id=filters.matrix_id,
                        entity_set_id=filters.entity_set_id,
                        query_vector=query_embedding,
                    )

                    return await self.vector_provider.vector_search_chunks(
                        query_vector=query_embedding,
                        filters=filters_with_vector,
                        skip=0,
                        limit=limit * 3,
                    )
                except Exception as e:
                    logger.warning(f"Vector search failed, using keyword-only: {e}")
                    return None

            # Run both searches in parallel
            keyword_results, vector_results = await asyncio.gather(
                run_keyword_search(),
                run_vector_search(),
            )

            # Combine results using RRF (Reciprocal Rank Fusion)
            if vector_results and vector_results.chunks:
                combined_chunks = self._reciprocal_rank_fusion(
                    keyword_results.chunks,
                    vector_results.chunks,
                )
            else:
                combined_chunks = keyword_results.chunks

            # Fetch actual content from S3 for top results
            final_chunks = await self._hydrate_chunk_content(
                combined_chunks[skip : skip + limit]
            )

            return ChunkSearchResult(
                chunks=final_chunks,
                total_count=len(combined_chunks),
                has_more=skip + limit < len(combined_chunks),
            )

        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return ChunkSearchResult(chunks=[], total_count=0, has_more=False)

    def _reciprocal_rank_fusion(
        self,
        keyword_results: List[ChunkSearchHit],
        vector_results: List[ChunkSearchHit],
        k: int = 60,
    ) -> List[ChunkSearchHit]:
        """
        Combine keyword and vector results using Reciprocal Rank Fusion.

        Args:
            keyword_results: Results from keyword search
            vector_results: Results from vector search
            k: RRF constant (default: 60)

        Returns:
            Combined and re-ranked results
        """
        scores = {}

        # Score keyword results
        for rank, hit in enumerate(keyword_results, start=1):
            key = f"{hit.document_id}_{hit.chunk_id}"
            scores[key] = scores.get(
                key,
                {
                    "hit": hit,
                    "score": 0,
                },
            )
            scores[key]["score"] += 1.0 / (k + rank)

        # Score vector results
        for rank, hit in enumerate(vector_results, start=1):
            key = f"{hit.document_id}_{hit.chunk_id}"
            scores[key] = scores.get(
                key,
                {
                    "hit": hit,
                    "score": 0,
                },
            )
            scores[key]["score"] += 1.0 / (k + rank)

        # Sort by combined score
        sorted_results = sorted(
            scores.values(),
            key=lambda x: x["score"],
            reverse=True,
        )

        # Update scores in hits
        for item in sorted_results:
            item["hit"].score = item["score"]

        return [item["hit"] for item in sorted_results]

    @trace_span
    async def _hydrate_chunk_content(
        self, chunk_hits: List[ChunkSearchHit]
    ) -> List[ChunkSearchHit]:
        """
        Fetch actual chunk content from S3 for search results.

        Args:
            chunk_hits: Search results without content

        Returns:
            Search results with content populated
        """
        if not chunk_hits:
            return []

        chunking_service = get_document_chunking_service()

        # Group chunks by document for efficient fetching
        chunks_by_doc = {}
        for hit in chunk_hits:
            if hit.document_id not in chunks_by_doc:
                chunks_by_doc[hit.document_id] = []
            chunks_by_doc[hit.document_id].append(hit)

        # Fetch content for each document's chunks
        hydrated_hits = []
        for document_id, hits in chunks_by_doc.items():
            try:
                # Get all chunks for this document
                chunks = await chunking_service.get_chunks_for_document(
                    document_id=document_id,
                    company_id=hits[0].company_id,
                )

                # Map chunk_id to content
                chunk_content_map = {c.chunk_id: c.content for c in chunks}

                # Populate content in hits
                for hit in hits:
                    hit.content = chunk_content_map.get(hit.chunk_id, "")
                    hydrated_hits.append(hit)

            except Exception as e:
                logger.error(f"Error fetching content for document {document_id}: {e}")
                # Add hits without content
                hydrated_hits.extend(hits)

        return hydrated_hits

    async def delete_chunk(self, chunk_id: str, document_id: int) -> bool:
        """
        Delete a chunk from both keyword and vector search indexes.

        Args:
            chunk_id: Chunk identifier
            document_id: Parent document ID

        Returns:
            True if deletion succeeded
        """
        keyword_success = await self.keyword_provider.delete_chunk_from_index(
            chunk_id, document_id
        )
        vector_success = await self.vector_provider.delete_chunk_embedding(
            chunk_id, document_id
        )
        return keyword_success and vector_success


def get_chunk_search_service() -> ChunkSearchService:
    """Get chunk search service instance."""
    return ChunkSearchService()
