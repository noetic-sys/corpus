"""Turbopuffer document search implementation (BM25 full-text search on documents)."""

import asyncio
from typing import List, Optional
from datetime import datetime

import turbopuffer

from .interface import (
    DocumentSearchInterface,
    DocumentSearchResult,
    DocumentSearchFilters,
)
from .types import ChunkSearchResult, ChunkSearchFilters, ChunkSearchHit
from packages.documents.models.domain.document import DocumentModel
from common.core.otel_axiom_exporter import get_logger, trace_span

logger = get_logger(__name__)

DOCUMENT_SCHEMA = {
    "doc_id": {"type": "uint", "filterable": True},
    "company_id": {"type": "uint", "filterable": True},
    "filename": {
        "type": "string",
        "full_text_search": {"tokenizer": "unicode61", "stemming": False},
    },
    "content_type": {"type": "string", "filterable": True},
    "extraction_status": {"type": "string", "filterable": True},
    "file_size": {"type": "uint", "filterable": False},
    "checksum": {"type": "string", "filterable": False},
    "storage_key": {"type": "string", "filterable": False},
    "extracted_content": {
        "type": "string",
        "full_text_search": {
            "tokenizer": "unicode61",
            "stemming": True,
            "language": "english",
        },
    },
    "created_at": {"type": "string", "filterable": True},
    "updated_at": {"type": "string", "filterable": True},
}

CHUNKS_SCHEMA = {
    "chunk_id": {"type": "string", "filterable": True},
    "document_id": {"type": "uint", "filterable": True},
    "company_id": {"type": "uint", "filterable": True},
    "matrix_id": {"type": "uint", "filterable": True},
    "entity_set_id": {"type": "uint", "filterable": True},
    "content": {
        "type": "string",
        "full_text_search": {
            "tokenizer": "unicode61",
            "stemming": True,
            "language": "english",
        },
    },
}


class TurbopufferDocumentSearch(DocumentSearchInterface):
    """Turbopuffer-based document search implementation."""

    def __init__(self, api_key: str, embedding_dim: int = 1536):
        self.api_key = api_key
        self.doc_namespace_prefix = "corpus_documents"
        self.chunks_namespace_prefix = "corpus_chunks"
        self.embedding_dim = embedding_dim

    def _doc_ns(self, company_id: int = None) -> turbopuffer.Namespace:
        name = f"{self.doc_namespace_prefix}_{company_id}" if company_id else self.doc_namespace_prefix
        return turbopuffer.Namespace(name, api_key=self.api_key)

    def _chunks_ns(self, company_id: int = None) -> turbopuffer.Namespace:
        name = f"{self.chunks_namespace_prefix}_{company_id}" if company_id else self.chunks_namespace_prefix
        return turbopuffer.Namespace(name, api_key=self.api_key)

    def _row_to_document(self, row) -> DocumentModel:
        """Convert a turbopuffer row to DocumentModel."""
        attrs = row if isinstance(row, dict) else row.__dict__

        def _parse_dt(val):
            if not val:
                return None
            if isinstance(val, datetime):
                return val
            return datetime.fromisoformat(str(val).replace("Z", "+00:00"))

        return DocumentModel(
            id=attrs.get("doc_id", 0),
            filename=attrs.get("filename", ""),
            storage_key=attrs.get("storage_key", ""),
            content_type=attrs.get("content_type"),
            file_size=attrs.get("file_size"),
            checksum=attrs.get("checksum", ""),
            company_id=attrs.get("company_id", 0),
            extraction_status=attrs.get("extraction_status", "pending"),
            created_at=_parse_dt(attrs.get("created_at")) or datetime.utcnow(),
            updated_at=_parse_dt(attrs.get("updated_at")) or datetime.utcnow(),
        )

    @trace_span
    async def search_documents(
        self,
        query: Optional[str] = None,
        filters: Optional[DocumentSearchFilters] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> DocumentSearchResult:
        """Search documents using Turbopuffer BM25."""
        try:
            company_id = filters.company_id if filters else None
            ns = self._doc_ns(company_id)

            filter_conditions = []
            if filters:
                filter_conditions.append(("company_id", "Eq", filters.company_id))
                if filters.content_type:
                    filter_conditions.append(("content_type", "Eq", filters.content_type))
                if filters.extraction_status:
                    filter_conditions.append(("extraction_status", "Eq", filters.extraction_status))

            tpuf_filters = None
            if len(filter_conditions) == 1:
                tpuf_filters = filter_conditions[0]
            elif len(filter_conditions) > 1:
                tpuf_filters = ("And", filter_conditions)

            fetch_count = skip + limit

            if query:
                rank_by = (
                    "Sum",
                    [
                        ("Product", 3, ("filename", "BM25", query)),
                        ("extracted_content", "BM25", query),
                    ],
                )
                result = await asyncio.to_thread(
                    ns.query,
                    rank_by=rank_by,
                    top_k=fetch_count,
                    filters=tpuf_filters,
                    include_attributes=True,
                )
            else:
                result = await asyncio.to_thread(
                    ns.query,
                    rank_by=("created_at", "desc"),
                    top_k=fetch_count,
                    filters=tpuf_filters,
                    include_attributes=True,
                )

            rows = result.rows[skip:] if result.rows else []
            documents = [self._row_to_document(row) for row in rows[:limit]]
            total_count = len(result.rows) if result.rows else 0
            has_more = total_count > skip + limit

            return DocumentSearchResult(
                documents=documents, total_count=total_count, has_more=has_more
            )

        except Exception as e:
            logger.error(f"Turbopuffer document search failed: {e}")
            return DocumentSearchResult(documents=[], total_count=0, has_more=False)

    @trace_span
    async def list_documents(
        self,
        filters: Optional[DocumentSearchFilters] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> DocumentSearchResult:
        """List all documents with optional filters."""
        return await self.search_documents(
            query=None, filters=filters, skip=skip, limit=limit
        )

    @trace_span
    async def get_supported_filters(self) -> List[str]:
        """Get list of supported filter types."""
        return ["content_type", "extraction_status", "created_after", "created_before"]

    @trace_span
    async def health_check(self) -> bool:
        """Check if Turbopuffer is available."""
        try:
            namespaces = await asyncio.to_thread(turbopuffer.namespaces)
            return True
        except Exception as e:
            logger.error(f"Turbopuffer health check failed: {e}")
            return False

    async def index_document(
        self, document: DocumentModel, extracted_content: str = None
    ) -> bool:
        """Index a document in Turbopuffer."""
        try:
            ns = self._doc_ns(document.company_id)
            row = {
                "id": str(document.id),
                "doc_id": document.id,
                "company_id": document.company_id,
                "filename": document.filename,
                "content_type": document.content_type or "",
                "extraction_status": str(document.extraction_status),
                "file_size": document.file_size or 0,
                "checksum": document.checksum,
                "storage_key": document.storage_key,
                "created_at": document.created_at.isoformat() if document.created_at else "",
                "updated_at": document.updated_at.isoformat() if document.updated_at else "",
            }
            if extracted_content:
                row["extracted_content"] = extracted_content

            await asyncio.to_thread(
                ns.write,
                upsert_rows=[row],
                distance_metric="cosine_distance",
                schema=DOCUMENT_SCHEMA,
            )
            logger.info(f"Indexed document {document.id} in Turbopuffer")
            return True
        except Exception as e:
            logger.error(f"Failed to index document {document.id}: {e}")
            return False

    async def delete_document_from_index(self, document_id: int) -> bool:
        """Delete a document from Turbopuffer."""
        try:
            ns = self._doc_ns()
            await asyncio.to_thread(ns.write, deletes=[str(document_id)])
            logger.info(f"Deleted document {document_id} from Turbopuffer")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False

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
            ns = self._chunks_ns(company_id)
            doc_id = f"{document_id}_{chunk_id}"
            row = {
                "id": doc_id,
                "chunk_id": chunk_id,
                "document_id": document_id,
                "company_id": company_id,
                "matrix_id": metadata.get("matrix_id"),
                "entity_set_id": metadata.get("entity_set_id"),
                "content": content,
            }
            if embedding:
                row["vector"] = embedding

            await asyncio.to_thread(
                ns.write,
                upsert_rows=[row],
                distance_metric="cosine_distance",
                schema=CHUNKS_SCHEMA,
            )
            logger.debug(f"Indexed chunk {chunk_id} for document {document_id}")
            return True
        except Exception as e:
            logger.error(f"Error indexing chunk {chunk_id}: {e}")
            return False

    async def index_chunks_bulk(self, chunks: List[dict]) -> bool:
        """Bulk index multiple chunks."""
        try:
            by_company: dict[int, list] = {}
            for chunk in chunks:
                cid = chunk["company_id"]
                by_company.setdefault(cid, []).append(chunk)

            for company_id, company_chunks in by_company.items():
                ns = self._chunks_ns(company_id)
                rows = []
                for chunk in company_chunks:
                    doc_id = f"{chunk['document_id']}_{chunk['chunk_id']}"
                    row = {
                        "id": doc_id,
                        "chunk_id": chunk["chunk_id"],
                        "document_id": chunk["document_id"],
                        "company_id": chunk["company_id"],
                        "matrix_id": chunk["metadata"].get("matrix_id"),
                        "entity_set_id": chunk["metadata"].get("entity_set_id"),
                        "content": chunk["content"],
                    }
                    if chunk.get("embedding"):
                        row["vector"] = chunk["embedding"]
                    rows.append(row)

                await asyncio.to_thread(
                    ns.write,
                    upsert_rows=rows,
                    distance_metric="cosine_distance",
                    schema=CHUNKS_SCHEMA,
                )

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
        """Hybrid search chunks using BM25 + vector if available."""
        try:
            ns = self._chunks_ns(filters.company_id)

            filter_conditions = [("company_id", "Eq", filters.company_id)]
            if filters.document_ids:
                filter_conditions.append(("document_id", "In", filters.document_ids))
            if filters.matrix_id:
                filter_conditions.append(("matrix_id", "Eq", filters.matrix_id))
            if filters.entity_set_id:
                filter_conditions.append(("entity_set_id", "Eq", filters.entity_set_id))

            tpuf_filters = filter_conditions[0] if len(filter_conditions) == 1 else ("And", filter_conditions)
            fetch_count = skip + limit

            if filters.query_vector:
                rank_by = (
                    "Sum",
                    [
                        ("content", "BM25", query),
                        ("vector", "ANN", filters.query_vector),
                    ],
                )
            else:
                rank_by = ("content", "BM25", query)

            result = await asyncio.to_thread(
                ns.query,
                rank_by=rank_by,
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
                        content=content,
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
            logger.error(f"Error searching chunks: {e}")
            return ChunkSearchResult(chunks=[], total_count=0, has_more=False)

    async def delete_chunk_from_index(self, chunk_id: str, document_id: int) -> bool:
        """Remove a chunk from the search index."""
        try:
            doc_id = f"{document_id}_{chunk_id}"
            ns = self._chunks_ns()
            await asyncio.to_thread(ns.write, deletes=[doc_id])
            logger.debug(f"Deleted chunk {chunk_id} from index")
            return True
        except Exception as e:
            logger.error(f"Error deleting chunk {chunk_id}: {e}")
            return False
