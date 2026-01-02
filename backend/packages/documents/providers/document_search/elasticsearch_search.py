from typing import List, Optional, Dict, Any
from datetime import datetime
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError

from .interface import (
    DocumentSearchInterface,
    DocumentSearchResult,
    DocumentSearchFilters,
)
from .types import ChunkSearchResult, ChunkSearchFilters, ChunkSearchHit
from packages.documents.models.domain.document import DocumentModel
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class ElasticsearchDocumentSearch(DocumentSearchInterface):
    """Elasticsearch-based document search implementation."""

    def __init__(self, elasticsearch_url: str = "http://localhost:9200"):
        # The AsyncElasticsearch client handles connection pooling internally
        # Each instance manages its own connection pool efficiently
        self.es_client = AsyncElasticsearch(
            [elasticsearch_url],
            verify_certs=False,
            ssl_show_warn=False,
            # Connection settings for proper cleanup
            request_timeout=30,
            max_retries=3,
            retry_on_timeout=True,
        )
        self.index_name = "documents"
        self.chunks_index_name = "chunks"

    async def _ensure_index_exists(self):
        """Ensure the documents index exists with proper mapping."""
        try:
            if not await self.es_client.indices.exists(index=self.index_name):
                mapping = {
                    "mappings": {
                        "properties": {
                            "id": {"type": "long"},
                            "company_id": {"type": "long"},
                            "filename": {
                                "type": "text",
                                "analyzer": "standard",
                                "fields": {
                                    "keyword": {"type": "keyword"},
                                    "search": {
                                        "type": "text",
                                        "analyzer": "standard",
                                        "search_analyzer": "standard",
                                    },
                                },
                            },
                            "content_type": {"type": "keyword"},
                            "extraction_status": {"type": "keyword"},
                            "file_size": {"type": "long"},
                            "checksum": {"type": "keyword"},
                            "storage_key": {"type": "keyword"},
                            "extracted_content_path": {"type": "keyword"},
                            "extraction_started_at": {"type": "date"},
                            "extraction_completed_at": {"type": "date"},
                            "created_at": {"type": "date"},
                            "updated_at": {"type": "date"},
                            "extracted_content": {
                                "type": "text",
                                "analyzer": "standard",
                                "fields": {
                                    "keyword": {"type": "keyword"},
                                    "search": {
                                        "type": "text",
                                        "analyzer": "standard",
                                        "search_analyzer": "standard",
                                    },
                                },
                            },
                        }
                    }
                }
                await self.es_client.indices.create(index=self.index_name, body=mapping)
                logger.info(f"Created Elasticsearch index: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to ensure index exists: {e}")

    def _build_query(
        self, search_term: Optional[str], filters: Optional[DocumentSearchFilters]
    ) -> Dict[str, Any]:
        """Build Elasticsearch query."""
        # If no search term and no filters, match all documents
        if not search_term and not filters:
            return {"match_all": {}}

        query = {"bool": {}}

        # Add search term if provided
        if search_term:
            query["bool"]["should"] = [
                # Search in filename with different analyzers
                {
                    "match": {
                        "filename": {
                            "query": search_term,
                            "boost": 3,
                            "fuzziness": "AUTO",
                        }
                    }
                },
                {
                    "match": {
                        "filename.search": {
                            "query": search_term,
                            "boost": 2,
                            "fuzziness": "AUTO",
                        }
                    }
                },
                # Search in extracted content (only if field exists)
                {
                    "match": {
                        "extracted_content": {
                            "query": search_term,
                            "boost": 1,
                            "fuzziness": "AUTO",
                        }
                    }
                },
                # Prefix match for partial searches
                {"prefix": {"filename": search_term.lower()}},
                # Wildcard as fallback
                {"wildcard": {"filename": f"*{search_term.lower()}*"}},
            ]
            query["bool"]["minimum_should_match"] = 1

        # Add filters
        if filters:
            query["bool"]["filter"] = []

            # Always filter by company_id for data federation
            query["bool"]["filter"].append({"term": {"company_id": filters.company_id}})

            if filters.content_type:
                query["bool"]["filter"].append(
                    {"term": {"content_type": filters.content_type}}
                )

            if filters.extraction_status:
                query["bool"]["filter"].append(
                    {"term": {"extraction_status": filters.extraction_status}}
                )

            if filters.created_after:
                try:
                    after_date = datetime.fromisoformat(filters.created_after)
                    query["bool"]["filter"].append(
                        {"range": {"created_at": {"gte": after_date.isoformat()}}}
                    )
                except ValueError:
                    logger.warning(
                        f"Invalid date format for created_after: {filters.created_after}"
                    )

            if filters.created_before:
                try:
                    before_date = datetime.fromisoformat(filters.created_before)
                    query["bool"]["filter"].append(
                        {"range": {"created_at": {"lte": before_date.isoformat()}}}
                    )
                except ValueError:
                    logger.warning(
                        f"Invalid date format for created_before: {filters.created_before}"
                    )

        return query

    def _hit_to_document(self, hit: Dict[str, Any]) -> DocumentModel:
        """Convert Elasticsearch hit to DocumentModel."""
        source = hit["_source"]

        # Parse datetime fields
        for date_field in [
            "created_at",
            "updated_at",
            "extraction_started_at",
            "extraction_completed_at",
        ]:
            if source.get(date_field):
                source[date_field] = datetime.fromisoformat(
                    source[date_field].replace("Z", "+00:00")
                )

        return DocumentModel.model_validate(source)

    @trace_span
    async def search_documents(
        self,
        query: Optional[str] = None,
        filters: Optional[DocumentSearchFilters] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> DocumentSearchResult:
        """Search documents using Elasticsearch."""
        logger.info(
            f"Elasticsearch search with query='{query}', skip={skip}, limit={limit}"
        )

        try:
            await self._ensure_index_exists()

            es_query = self._build_query(query, filters)

            # Build complete search body
            search_body = {
                "query": es_query,
                "from": skip,
                "size": limit,
                "sort": [{"created_at": {"order": "desc"}}],
                "track_total_hits": True,
            }

            # Log the complete query body for debugging
            logger.info(f"Elasticsearch query body: {search_body}")

            # Also log index mapping for debugging (only on first search)
            if query and not hasattr(self, "_mapping_logged"):
                try:
                    mapping = await self.es_client.indices.get_mapping(
                        index=self.index_name
                    )
                    logger.info(f"Elasticsearch index mapping: {mapping}")
                    self._mapping_logged = True
                except Exception as e:
                    logger.warning(f"Could not get index mapping: {e}")

            # Execute search
            response = await self.es_client.search(
                index=self.index_name, body=search_body
            )

            # Parse results
            hits = response["hits"]["hits"]
            documents = [self._hit_to_document(hit) for hit in hits]

            total_count = response["hits"]["total"]["value"]
            has_more = (skip + len(documents)) < total_count

            logger.info(
                f"Elasticsearch found {len(documents)} documents out of {total_count} total"
            )

            return DocumentSearchResult(
                documents=documents, total_count=total_count, has_more=has_more
            )

        except Exception as e:
            logger.error(f"Elasticsearch search failed: {e}")
            # Return empty results on error
            return DocumentSearchResult(documents=[], total_count=0, has_more=False)

    @trace_span
    async def list_documents(
        self,
        filters: Optional[DocumentSearchFilters] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> DocumentSearchResult:
        """List all documents with optional filters."""
        logger.info(f"Elasticsearch list documents with skip={skip}, limit={limit}")

        # List documents is just search without a query term
        return await self.search_documents(
            query=None, filters=filters, skip=skip, limit=limit
        )

    @trace_span
    async def get_supported_filters(self) -> List[str]:
        """Get list of supported filter types."""
        return ["content_type", "extraction_status", "created_after", "created_before"]

    @trace_span
    async def health_check(self) -> bool:
        """Check if Elasticsearch is available and healthy."""
        try:
            health = await self.es_client.cluster.health()
            return health["status"] in ["green", "yellow"]
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return False

    async def index_document(
        self, document: DocumentModel, extracted_content: str = None
    ) -> bool:
        """Index a document in Elasticsearch."""
        try:
            await self._ensure_index_exists()

            doc_dict = document.model_dump()
            # Convert datetime objects to ISO strings
            for date_field in [
                "created_at",
                "updated_at",
                "extraction_started_at",
                "extraction_completed_at",
            ]:
                if doc_dict.get(date_field):
                    doc_dict[date_field] = doc_dict[date_field].isoformat()

            # Add extracted content if provided
            if extracted_content:
                doc_dict["extracted_content"] = extracted_content

            await self.es_client.index(
                index=self.index_name, id=document.id, body=doc_dict
            )
            logger.info(f"Indexed document {document.id} in Elasticsearch")
            return True
        except Exception as e:
            logger.error(f"Failed to index document {document.id}: {e}")
            return False

    async def delete_document_from_index(self, document_id: int) -> bool:
        """Delete a document from Elasticsearch."""
        try:
            await self.es_client.delete(index=self.index_name, id=document_id)
            logger.info(f"Deleted document {document_id} from Elasticsearch")
            return True
        except NotFoundError:
            logger.info(f"Document {document_id} not found in Elasticsearch")
            return True  # Consider not found as success
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False

    async def _ensure_chunks_index_exists(self):
        """Ensure the chunks index exists with proper mapping for hybrid search."""
        try:
            if not await self.es_client.indices.exists(index=self.chunks_index_name):
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
                                    "search": {
                                        "type": "text",
                                        "analyzer": "standard",
                                        "search_analyzer": "standard",
                                    },
                                },
                            },
                            "metadata": {"type": "object", "enabled": True},
                            "embedding": {
                                "type": "dense_vector",
                                "dims": 1536,  # OpenAI text-embedding-3-small default
                                "index": True,
                                "similarity": "cosine",
                            },
                            "created_at": {"type": "date"},
                        }
                    }
                }
                await self.es_client.indices.create(
                    index=self.chunks_index_name, body=mapping
                )
                logger.info(f"Created chunks index: {self.chunks_index_name}")
        except Exception as e:
            logger.error(f"Error ensuring chunks index exists: {e}")
            raise

    async def index_chunk(
        self,
        chunk_id: str,
        document_id: int,
        company_id: int,
        content: str,
        metadata: dict,
        embedding: Optional[List[float]] = None,
    ) -> bool:
        """Index a single chunk with optional vector embedding."""
        try:
            await self._ensure_chunks_index_exists()

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

            # Only add embedding if provided (graceful degradation)
            if embedding:
                doc["embedding"] = embedding

            # Use document_id + chunk_id as unique identifier
            doc_id = f"{document_id}_{chunk_id}"

            await self.es_client.index(
                index=self.chunks_index_name, id=doc_id, document=doc
            )
            logger.debug(f"Indexed chunk {chunk_id} for document {document_id}")
            return True
        except Exception as e:
            logger.error(f"Error indexing chunk {chunk_id}: {e}")
            return False

    async def index_chunks_bulk(self, chunks: List[dict]) -> bool:
        """Bulk index multiple chunks."""
        try:
            await self._ensure_chunks_index_exists()

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

                # Only add embedding if provided
                if chunk.get("embedding"):
                    doc["embedding"] = chunk["embedding"]

                bulk_actions.append(
                    {"index": {"_index": self.chunks_index_name, "_id": doc_id}}
                )
                bulk_actions.append(doc)

            if bulk_actions:
                await self.es_client.bulk(operations=bulk_actions)
                logger.info(f"Bulk indexed {len(chunks)} chunks")
            return True
        except Exception as e:
            logger.error(f"Error bulk indexing chunks: {e}")
            return False

    async def search_chunks(
        self,
        query: str,
        filters: ChunkSearchFilters,
        skip: int = 0,
        limit: int = 10,
    ) -> ChunkSearchResult:
        """
        Hybrid search chunks using BM25 (keyword) + kNN (vector) if available.
        Falls back to keyword-only if no embedding in query.
        """
        try:
            await self._ensure_chunks_index_exists()

            # Build filter query
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

            # Build search query
            if filters.query_vector:
                # Hybrid search: BM25 + kNN
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
                    "knn": {
                        "field": "embedding",
                        "query_vector": filters.query_vector,
                        "k": limit * 2,  # Retrieve more for hybrid ranking
                        "num_candidates": 100,
                        "filter": {"bool": {"filter": filter_conditions}},
                    },
                    "rank": {"rrf": {}},  # Reciprocal Rank Fusion for hybrid
                    "from": skip,
                    "size": limit,
                    "highlight": {
                        "fields": {
                            "content": {"fragment_size": 150, "number_of_fragments": 3}
                        }
                    },
                }
            else:
                # Keyword-only search (graceful fallback)
                logger.info("No embedding provided, using keyword-only search")
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
                index=self.chunks_index_name, body=search_body
            )

            # Parse results
            chunks = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                highlights = hit.get("highlight", {}).get("content", [])

                chunks.append(
                    ChunkSearchHit(
                        chunk_id=source["chunk_id"],
                        document_id=source["document_id"],
                        company_id=source["company_id"],
                        content=source["content"],
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
            logger.error(f"Error searching chunks: {e}")
            # Return empty result on error
            return ChunkSearchResult(chunks=[], total_count=0, has_more=False)

    async def delete_chunk_from_index(self, chunk_id: str, document_id: int) -> bool:
        """Remove a chunk from the search index."""
        try:
            doc_id = f"{document_id}_{chunk_id}"
            await self.es_client.delete(index=self.chunks_index_name, id=doc_id)
            logger.debug(f"Deleted chunk {chunk_id} from index")
            return True
        except NotFoundError:
            logger.warning(f"Chunk {chunk_id} not found in index")
            return False
        except Exception as e:
            logger.error(f"Error deleting chunk {chunk_id}: {e}")
            return False

    async def close(self):
        """Close the Elasticsearch client."""
        try:
            await self.es_client.close()
            logger.debug("Elasticsearch client closed successfully")
        except Exception as e:
            logger.warning(f"Error closing Elasticsearch client: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
