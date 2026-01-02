"""Elasticsearch keyword search implementation (BM25)."""

from typing import List
from datetime import datetime
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError

from packages.documents.providers.document_search.keyword_search_interface import (
    KeywordSearchInterface,
)
from packages.documents.providers.document_search.types import (
    ChunkSearchResult,
    ChunkSearchFilters,
    ChunkSearchHit,
)
from common.core.otel_axiom_exporter import get_logger, trace_span

logger = get_logger(__name__)


class ElasticsearchKeywordSearch(KeywordSearchInterface):
    """Elasticsearch-based keyword search using BM25."""

    def __init__(self, elasticsearch_url: str = "http://localhost:9200"):
        self.es_client = AsyncElasticsearch(
            [elasticsearch_url],
            verify_certs=False,
            ssl_show_warn=False,
            request_timeout=30,
            max_retries=3,
            retry_on_timeout=True,
        )
        self.index_name = "chunks_keyword"

    async def _ensure_index_exists(self):
        """Ensure the keyword search index exists."""
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
                            "content": {
                                "type": "text",
                                "analyzer": "standard",
                                "fields": {
                                    "keyword": {"type": "keyword"},
                                },
                            },
                            "metadata": {"type": "object", "enabled": True},
                            "created_at": {"type": "date"},
                        }
                    }
                }
                await self.es_client.indices.create(index=self.index_name, body=mapping)
                logger.info(f"Created keyword search index: {self.index_name}")
        except Exception as e:
            logger.error(f"Error ensuring keyword index exists: {e}")
            raise

    async def index_chunk(
        self,
        chunk_id: str,
        document_id: int,
        company_id: int,
        content: str,
        metadata: dict,
    ) -> bool:
        """Index a chunk for keyword search."""
        try:
            await self._ensure_index_exists()

            doc = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "company_id": company_id,
                "matrix_id": metadata.get("matrix_id"),
                "entity_set_id": metadata.get("entity_set_id"),
                "content": content,
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat(),
            }

            doc_id = f"{document_id}_{chunk_id}"
            await self.es_client.index(index=self.index_name, id=doc_id, document=doc)
            logger.debug(f"Indexed chunk {chunk_id} for keyword search")
            return True
        except Exception as e:
            logger.error(f"Error indexing chunk {chunk_id} for keyword search: {e}")
            return False

    async def index_chunks_bulk(self, chunks: List[dict]) -> bool:
        """Bulk index chunks for keyword search."""
        try:
            await self._ensure_index_exists()

            bulk_actions = []
            for chunk in chunks:
                doc_id = f"{chunk['document_id']}_{chunk['chunk_id']}"
                doc = {
                    "chunk_id": chunk["chunk_id"],
                    "document_id": chunk["document_id"],
                    "company_id": chunk["company_id"],
                    "matrix_id": chunk["metadata"].get("matrix_id"),
                    "entity_set_id": chunk["metadata"].get("entity_set_id"),
                    "content": chunk["content"],
                    "metadata": chunk["metadata"],
                    "created_at": datetime.utcnow().isoformat(),
                }

                bulk_actions.append(
                    {"index": {"_index": self.index_name, "_id": doc_id}}
                )
                bulk_actions.append(doc)

            if bulk_actions:
                await self.es_client.bulk(operations=bulk_actions)
                logger.info(f"Bulk indexed {len(chunks)} chunks for keyword search")
            return True
        except Exception as e:
            logger.error(f"Error bulk indexing chunks for keyword search: {e}")
            return False

    @trace_span
    async def keyword_search_chunks(
        self,
        query: str,
        filters: ChunkSearchFilters,
        skip: int = 0,
        limit: int = 10,
    ) -> ChunkSearchResult:
        """Search chunks using BM25 keyword matching."""
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

            # BM25 keyword search
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["content^2", "metadata.section"],
                                }
                            }
                        ],
                        "filter": filter_conditions,
                    }
                },
                "from": skip,
                "size": limit,
                "highlight": {
                    "fields": {
                        "content": {"fragment_size": 150, "number_of_fragments": 3}
                    }
                },
            }

            response = await self.es_client.search(
                index=self.index_name, body=search_body
            )

            # Parse results (without content - that comes from S3)
            chunks = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                highlights = hit.get("highlight", {}).get("content", [])

                chunks.append(
                    ChunkSearchHit(
                        chunk_id=source["chunk_id"],
                        document_id=source["document_id"],
                        company_id=source["company_id"],
                        content="",  # Content fetched separately from S3
                        metadata=source["metadata"],
                        score=hit["_score"],
                        highlights=highlights,
                    )
                )

            total_count = response["hits"]["total"]["value"]
            has_more = skip + limit < total_count

            return ChunkSearchResult(
                chunks=chunks, total_count=total_count, has_more=has_more
            )

        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return ChunkSearchResult(chunks=[], total_count=0, has_more=False)

    async def delete_chunk_from_index(self, chunk_id: str, document_id: int) -> bool:
        """Remove chunk from keyword search index."""
        try:
            doc_id = f"{document_id}_{chunk_id}"
            await self.es_client.delete(index=self.index_name, id=doc_id)
            logger.debug(f"Deleted chunk {chunk_id} from keyword index")
            return True
        except NotFoundError:
            logger.warning(f"Chunk {chunk_id} not found in keyword index")
            return False
        except Exception as e:
            logger.error(f"Error deleting chunk {chunk_id} from keyword index: {e}")
            return False

    async def close(self):
        """Close Elasticsearch client."""
        try:
            await self.es_client.close()
        except Exception as e:
            logger.warning(f"Error closing Elasticsearch client: {e}")
