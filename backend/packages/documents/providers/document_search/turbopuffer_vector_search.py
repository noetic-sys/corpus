"""Turbopuffer vector search implementation (ANN with cosine similarity)."""

import asyncio
from typing import List

import turbopuffer

from packages.documents.providers.document_search.vector_search_interface import (
    VectorSearchInterface,
)
from packages.documents.providers.document_search.types import (
    ChunkSearchResult,
    ChunkSearchFilters,
    ChunkSearchHit,
)
from common.core.otel_axiom_exporter import get_logger, trace_span

logger = get_logger(__name__)


class TurbopufferVectorSearch(VectorSearchInterface):
    """Turbopuffer-based vector search using ANN."""

    def __init__(self, api_key: str, embedding_dim: int = 1536):
        self.api_key = api_key
        self.namespace_prefix = "corpus_vectors"
        self.embedding_dim = embedding_dim

    def _ns(self, company_id: int = None) -> turbopuffer.Namespace:
        """Get a turbopuffer namespace, optionally scoped to a company."""
        name = f"{self.namespace_prefix}_{company_id}" if company_id else self.namespace_prefix
        return turbopuffer.Namespace(name, api_key=self.api_key)

    def _build_filters(self, filters: ChunkSearchFilters):
        """Build turbopuffer filter tuple from ChunkSearchFilters."""
        conditions = [("company_id", "Eq", filters.company_id)]

        if filters.document_ids:
            conditions.append(("document_id", "In", filters.document_ids))
        if filters.matrix_id:
            conditions.append(("matrix_id", "Eq", filters.matrix_id))
        if filters.entity_set_id:
            conditions.append(("entity_set_id", "Eq", filters.entity_set_id))

        if len(conditions) == 1:
            return conditions[0]
        return ("And", conditions)

    async def index_chunk_embedding(
        self,
        chunk_id: str,
        document_id: int,
        company_id: int,
        embedding: List[float],
        metadata: dict,
    ) -> bool:
        """Index a chunk embedding for vector search."""
        try:
            ns = self._ns(company_id)
            doc_id = f"{document_id}_{chunk_id}"

            await asyncio.to_thread(
                ns.write,
                upsert_rows=[
                    {
                        "id": doc_id,
                        "vector": embedding,
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "company_id": company_id,
                        "matrix_id": metadata.get("matrix_id"),
                        "entity_set_id": metadata.get("entity_set_id"),
                    }
                ],
                distance_metric="cosine_distance",
            )
            logger.debug(f"Indexed embedding for chunk {chunk_id}")
            return True
        except Exception as e:
            logger.error(f"Error indexing embedding for chunk {chunk_id}: {e}")
            return False

    async def index_embeddings_bulk(self, embeddings: List[dict]) -> bool:
        """Bulk index chunk embeddings."""
        try:
            by_company: dict[int, list] = {}
            for emb in embeddings:
                cid = emb["company_id"]
                by_company.setdefault(cid, []).append(emb)

            for company_id, embs in by_company.items():
                ns = self._ns(company_id)
                rows = []
                for emb in embs:
                    doc_id = f"{emb['document_id']}_{emb['chunk_id']}"
                    rows.append(
                        {
                            "id": doc_id,
                            "vector": emb["embedding"],
                            "chunk_id": emb["chunk_id"],
                            "document_id": emb["document_id"],
                            "company_id": emb["company_id"],
                            "matrix_id": emb["metadata"].get("matrix_id"),
                            "entity_set_id": emb["metadata"].get("entity_set_id"),
                        }
                    )
                await asyncio.to_thread(
                    ns.write,
                    upsert_rows=rows,
                    distance_metric="cosine_distance",
                )

            logger.info(f"Bulk indexed {len(embeddings)} chunk embeddings")
            return True
        except Exception as e:
            logger.error(f"Error bulk indexing embeddings: {e}")
            return False

    @trace_span
    async def vector_search_chunks(
        self,
        query_vector: List[float],
        filters: ChunkSearchFilters,
        skip: int = 0,
        limit: int = 10,
    ) -> ChunkSearchResult:
        """Search chunks using vector similarity (ANN)."""
        try:
            ns = self._ns(filters.company_id)
            tpuf_filters = self._build_filters(filters)
            fetch_count = skip + limit

            result = await asyncio.to_thread(
                ns.query,
                rank_by=("vector", "ANN", query_vector),
                top_k=fetch_count,
                filters=tpuf_filters,
                include_attributes=True,
            )

            rows = result.rows[skip:] if result.rows else []
            chunks = []
            for row in rows[:limit]:
                attrs = row if isinstance(row, dict) else row.__dict__
                chunks.append(
                    ChunkSearchHit(
                        chunk_id=attrs.get("chunk_id", ""),
                        document_id=attrs.get("document_id", 0),
                        company_id=attrs.get("company_id", 0),
                        content="",  # Content fetched separately from S3
                        metadata={},
                        score=attrs.get("$dist", 0.0),
                        highlights=[],
                    )
                )

            total_count = len(result.rows) if result.rows else 0
            has_more = total_count > skip + limit

            return ChunkSearchResult(
                chunks=chunks, total_count=total_count, has_more=has_more
            )

        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return ChunkSearchResult(chunks=[], total_count=0, has_more=False)

    async def delete_chunk_embedding(self, chunk_id: str, document_id: int) -> bool:
        """Remove chunk embedding from vector search index."""
        try:
            doc_id = f"{document_id}_{chunk_id}"
            ns = self._ns()
            await asyncio.to_thread(ns.write, deletes=[doc_id])
            logger.debug(f"Deleted embedding for chunk {chunk_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting embedding for chunk {chunk_id}: {e}")
            return False

    def get_embedding_dimension(self) -> int:
        """Get expected embedding dimension."""
        return self.embedding_dim
