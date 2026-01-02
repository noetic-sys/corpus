"""Elasticsearch vector search implementation (kNN with cosine similarity)."""

from typing import List
from datetime import datetime
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError

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


class ElasticsearchVectorSearch(VectorSearchInterface):
    """Elasticsearch-based vector search using kNN."""

    def __init__(
        self,
        elasticsearch_url: str = "http://localhost:9200",
        embedding_dim: int = 1536,
    ):
        self.es_client = AsyncElasticsearch(
            [elasticsearch_url],
            verify_certs=False,
            ssl_show_warn=False,
            request_timeout=30,
            max_retries=3,
            retry_on_timeout=True,
        )
        self.index_name = "chunks_vector"
        self.embedding_dim = embedding_dim

    async def _ensure_index_exists(self):
        """Ensure the vector search index exists."""
        try:
            if not await self.es_client.indices.exists(index=self.index_name):
                mapping = {
                    "mappings": {
                        "properties": {
                            "chunk_id": {"type": "keyword"},
                            "document_id": {"type": "long"},
                            "company_id": {"type": "long"},
                            "matrix_id": {"type": "long"},
                            "entity_set_id": {"type": "long"},
                            "embedding": {
                                "type": "dense_vector",
                                "dims": self.embedding_dim,
                                "index": True,
                                "similarity": "cosine",
                            },
                            "metadata": {"type": "object", "enabled": True},
                            "created_at": {"type": "date"},
                        }
                    }
                }
                await self.es_client.indices.create(index=self.index_name, body=mapping)
                logger.info(f"Created vector search index: {self.index_name}")
        except Exception as e:
            logger.error(f"Error ensuring vector index exists: {e}")
            raise

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
            await self._ensure_index_exists()

            doc = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "company_id": company_id,
                "matrix_id": metadata.get("matrix_id"),
                "entity_set_id": metadata.get("entity_set_id"),
                "embedding": embedding,
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat(),
            }

            doc_id = f"{document_id}_{chunk_id}"
            await self.es_client.index(index=self.index_name, id=doc_id, document=doc)
            logger.debug(f"Indexed embedding for chunk {chunk_id}")
            return True
        except Exception as e:
            logger.error(f"Error indexing embedding for chunk {chunk_id}: {e}")
            return False

    async def index_embeddings_bulk(self, embeddings: List[dict]) -> bool:
        """Bulk index chunk embeddings."""
        try:
            await self._ensure_index_exists()

            bulk_actions = []
            for emb in embeddings:
                doc_id = f"{emb['document_id']}_{emb['chunk_id']}"
                doc = {
                    "chunk_id": emb["chunk_id"],
                    "document_id": emb["document_id"],
                    "company_id": emb["company_id"],
                    "matrix_id": emb["metadata"].get("matrix_id"),
                    "entity_set_id": emb["metadata"].get("entity_set_id"),
                    "embedding": emb["embedding"],
                    "metadata": emb["metadata"],
                    "created_at": datetime.utcnow().isoformat(),
                }

                bulk_actions.append(
                    {"index": {"_index": self.index_name, "_id": doc_id}}
                )
                bulk_actions.append(doc)

            if bulk_actions:
                await self.es_client.bulk(operations=bulk_actions)
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
        """Search chunks using vector similarity (kNN)."""
        try:
            await self._ensure_index_exists()

            # Build filter conditions
            filter_conditions = [{"term": {"company_id": filters.company_id}}]

            if filters.document_ids:
                filter_conditions.append(
                    {"terms": {"document_id": filters.document_ids}}
                )
            if filters.matrix_id:
                filter_conditions.append({"term": {"matrix_id": filters.matrix_id}})
            if filters.entity_set_id:
                filter_conditions.append(
                    {"term": {"entity_set_id": filters.entity_set_id}}
                )

            # kNN vector search
            search_body = {
                "knn": {
                    "field": "embedding",
                    "query_vector": query_vector,
                    "k": limit,
                    "num_candidates": limit * 10,  # Candidate pool for better results
                    "filter": {"bool": {"filter": filter_conditions}},
                },
                "from": skip,
                "size": limit,
            }

            response = await self.es_client.search(
                index=self.index_name, body=search_body
            )

            # Parse results (without content - that comes from S3)
            chunks = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]

                chunks.append(
                    ChunkSearchHit(
                        chunk_id=source["chunk_id"],
                        document_id=source["document_id"],
                        company_id=source["company_id"],
                        content="",  # Content fetched separately from S3
                        metadata=source["metadata"],
                        score=hit["_score"],
                        highlights=[],  # No highlights for vector search
                    )
                )

            total_count = response["hits"]["total"]["value"]
            has_more = skip + limit < total_count

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
            await self.es_client.delete(index=self.index_name, id=doc_id)
            logger.debug(f"Deleted embedding for chunk {chunk_id}")
            return True
        except NotFoundError:
            logger.warning(f"Embedding for chunk {chunk_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error deleting embedding for chunk {chunk_id}: {e}")
            return False

    def get_embedding_dimension(self) -> int:
        """Get expected embedding dimension."""
        return self.embedding_dim

    async def close(self):
        """Close Elasticsearch client."""
        try:
            await self.es_client.close()
        except Exception as e:
            logger.warning(f"Error closing Elasticsearch client: {e}")
