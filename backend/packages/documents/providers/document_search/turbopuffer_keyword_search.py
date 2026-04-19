"""Turbopuffer keyword search implementation (BM25 full-text search)."""

import asyncio
from typing import List

import turbopuffer

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

SCHEMA = {
    "chunk_id": {"type": "string", "filterable": True},
    "document_id": {"type": "uint", "filterable": True},
    "company_id": {"type": "uint", "filterable": True},
    "matrix_id": {"type": "uint", "filterable": True},
    "entity_set_id": {"type": "uint", "filterable": True},
    "content": {
        "type": "string",
        "full_text_search": {
            "tokenizer": "word_v3",
            "stemming": True,
            "language": "english",
        },
    },
}


class TurbopufferKeywordSearch(KeywordSearchInterface):
    """Turbopuffer-based keyword search using BM25."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.namespace_prefix = "corpus_chunks_keyword"

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
            ns = self._ns(company_id)
            doc_id = f"{document_id}_{chunk_id}"

            await asyncio.to_thread(
                ns.write,
                upsert_rows=[
                    {
                        "id": doc_id,
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "company_id": company_id,
                        "matrix_id": metadata.get("matrix_id"),
                        "entity_set_id": metadata.get("entity_set_id"),
                        "content": content,
                    }
                ],
                distance_metric="cosine_distance",
                schema=SCHEMA,
            )
            logger.debug(f"Indexed chunk {chunk_id} for keyword search")
            return True
        except Exception as e:
            logger.error(f"Error indexing chunk {chunk_id} for keyword search: {e}")
            return False

    async def index_chunks_bulk(self, chunks: List[dict]) -> bool:
        """Bulk index chunks for keyword search."""
        try:
            by_company: dict[int, list] = {}
            for chunk in chunks:
                cid = chunk["company_id"]
                by_company.setdefault(cid, []).append(chunk)

            for company_id, company_chunks in by_company.items():
                ns = self._ns(company_id)
                rows = []
                for chunk in company_chunks:
                    doc_id = f"{chunk['document_id']}_{chunk['chunk_id']}"
                    rows.append(
                        {
                            "id": doc_id,
                            "chunk_id": chunk["chunk_id"],
                            "document_id": chunk["document_id"],
                            "company_id": chunk["company_id"],
                            "matrix_id": chunk["metadata"].get("matrix_id"),
                            "entity_set_id": chunk["metadata"].get("entity_set_id"),
                            "content": chunk["content"],
                        }
                    )
                await asyncio.to_thread(
                    ns.write,
                    upsert_rows=rows,
                    distance_metric="cosine_distance",
                    schema=SCHEMA,
                )

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
            ns = self._ns(filters.company_id)
            tpuf_filters = self._build_filters(filters)
            fetch_count = skip + limit

            result = await asyncio.to_thread(
                ns.query,
                rank_by=("content", "BM25", query),
                top_k=fetch_count,
                filters=tpuf_filters,
                include_attributes=True,
            )

            rows = result.rows[skip:] if result.rows else []
            chunks = []
            for row in rows[:limit]:
                attrs = row if isinstance(row, dict) else row.__dict__
                content = attrs.get("content", "")

                highlights = []
                query_lower = query.lower()
                content_lower = content.lower()
                idx = content_lower.find(query_lower)
                if idx != -1:
                    start = max(0, idx - 75)
                    end = min(len(content), idx + len(query) + 75)
                    highlights.append(f"...{content[start:end]}...")

                chunks.append(
                    ChunkSearchHit(
                        chunk_id=attrs.get("chunk_id", ""),
                        document_id=attrs.get("document_id", 0),
                        company_id=attrs.get("company_id", 0),
                        content="",  # Content fetched separately from S3
                        metadata={},
                        score=attrs.get("$dist", 0.0),
                        highlights=highlights,
                    )
                )

            total_count = len(result.rows) if result.rows else 0
            has_more = total_count > skip + limit

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
            ns = self._ns()
            await asyncio.to_thread(ns.write, deletes=[doc_id])
            logger.debug(f"Deleted chunk {chunk_id} from keyword index")
            return True
        except Exception as e:
            logger.error(f"Error deleting chunk {chunk_id} from keyword index: {e}")
            return False
