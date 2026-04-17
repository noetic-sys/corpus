import pytest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from packages.documents.providers.document_search.turbopuffer_document_search import (
    TurbopufferDocumentSearch,
)
from packages.documents.providers.document_search.interface import DocumentSearchFilters
from packages.documents.providers.document_search.types import ChunkSearchFilters
from packages.documents.models.domain.document import DocumentModel


class TestTurbopufferDocumentSearch:
    """Tests for TurbopufferDocumentSearch with mocked Turbopuffer client."""

    @pytest.fixture
    def mock_doc_ns(self):
        ns = MagicMock()
        ns.write = MagicMock()
        ns.query = MagicMock()
        return ns

    @pytest.fixture
    def mock_chunks_ns(self):
        ns = MagicMock()
        ns.write = MagicMock()
        ns.query = MagicMock()
        return ns

    @pytest.fixture
    def provider(self, mock_doc_ns, mock_chunks_ns):
        with patch(
            "packages.documents.providers.document_search.turbopuffer_document_search.turbopuffer"
        ) as mock_tpuf:

            def namespace_router(name, api_key=None):
                if "documents" in name:
                    return mock_doc_ns
                return mock_chunks_ns

            mock_tpuf.Namespace.side_effect = namespace_router

            p = TurbopufferDocumentSearch(api_key="test-key")
            yield p

    @pytest.mark.asyncio
    async def test_index_document(self, provider, mock_doc_ns):
        mock_doc_ns.write.return_value = MagicMock(rows_affected=1)

        doc = DocumentModel(
            id=1,
            filename="test.pdf",
            storage_key="docs/test.pdf",
            content_type="application/pdf",
            file_size=1024,
            checksum="abc123",
            company_id=1,
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )

        result = await provider.index_document(doc, extracted_content="Test content")

        assert result is True
        mock_doc_ns.write.assert_called_once()
        row = mock_doc_ns.write.call_args[1]["upsert_rows"][0]
        assert row["filename"] == "test.pdf"
        assert row["extracted_content"] == "Test content"
        assert row["doc_id"] == 1

    @pytest.mark.asyncio
    async def test_index_document_failure(self, provider, mock_doc_ns):
        mock_doc_ns.write.side_effect = Exception("API error")

        doc = DocumentModel(
            id=1,
            filename="test.pdf",
            storage_key="docs/test.pdf",
            checksum="abc123",
            company_id=1,
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )

        result = await provider.index_document(doc)

        assert result is False

    @pytest.mark.asyncio
    async def test_search_documents(self, provider, mock_doc_ns):
        mock_row = SimpleNamespace(
            doc_id=1,
            filename="test.pdf",
            storage_key="docs/test.pdf",
            content_type="application/pdf",
            file_size=1024,
            checksum="abc123",
            company_id=1,
            extraction_status="completed",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            **{"$dist": 5.0},
        )
        mock_result = MagicMock()
        mock_result.rows = [mock_row]
        mock_doc_ns.query.return_value = mock_result

        filters = DocumentSearchFilters(company_id=1)
        result = await provider.search_documents(
            query="test", filters=filters, skip=0, limit=10
        )

        assert len(result.documents) == 1
        assert result.documents[0].filename == "test.pdf"

    @pytest.mark.asyncio
    async def test_search_documents_error(self, provider, mock_doc_ns):
        mock_doc_ns.query.side_effect = Exception("API error")

        filters = DocumentSearchFilters(company_id=1)
        result = await provider.search_documents(query="test", filters=filters)

        assert len(result.documents) == 0
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_list_documents(self, provider, mock_doc_ns):
        mock_result = MagicMock()
        mock_result.rows = []
        mock_doc_ns.query.return_value = mock_result

        filters = DocumentSearchFilters(company_id=1)
        result = await provider.list_documents(filters=filters)

        assert len(result.documents) == 0
        mock_doc_ns.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_document_from_index(self, provider, mock_doc_ns):
        mock_doc_ns.write.return_value = MagicMock(rows_affected=1)

        result = await provider.delete_document_from_index(document_id=1)

        assert result is True
        mock_doc_ns.write.assert_called_once()
        assert "1" in mock_doc_ns.write.call_args[1]["deletes"]

    @pytest.mark.asyncio
    async def test_index_chunk(self, provider, mock_chunks_ns):
        mock_chunks_ns.write.return_value = MagicMock(rows_affected=1)

        result = await provider.index_chunk(
            chunk_id="chunk-1",
            document_id=10,
            company_id=1,
            content="Chunk content here",
            metadata={"matrix_id": 5},
            embedding=[0.1] * 1536,
        )

        assert result is True
        row = mock_chunks_ns.write.call_args[1]["upsert_rows"][0]
        assert row["content"] == "Chunk content here"
        assert row["vector"] == [0.1] * 1536

    @pytest.mark.asyncio
    async def test_index_chunks_bulk(self, provider, mock_chunks_ns):
        mock_chunks_ns.write.return_value = MagicMock(rows_affected=2)

        chunks = [
            {
                "chunk_id": "c1",
                "document_id": 10,
                "company_id": 1,
                "content": "First",
                "metadata": {},
            },
            {
                "chunk_id": "c2",
                "document_id": 10,
                "company_id": 1,
                "content": "Second",
                "metadata": {},
                "embedding": [0.2] * 1536,
            },
        ]

        result = await provider.index_chunks_bulk(chunks)

        assert result is True
        rows = mock_chunks_ns.write.call_args[1]["upsert_rows"]
        assert len(rows) == 2
        # First chunk has no vector, second does
        assert "vector" not in rows[0]
        assert rows[1]["vector"] == [0.2] * 1536

    @pytest.mark.asyncio
    async def test_search_chunks_keyword_only(self, provider, mock_chunks_ns):
        mock_result = MagicMock()
        mock_result.rows = []
        mock_chunks_ns.query.return_value = mock_result

        filters = ChunkSearchFilters(company_id=1)
        result = await provider.search_chunks(query="test", filters=filters)

        assert len(result.chunks) == 0
        call_kwargs = mock_chunks_ns.query.call_args[1]
        # Without query_vector, should use BM25 only
        rank_by = call_kwargs["rank_by"]
        assert rank_by == ("content", "BM25", "test")

    @pytest.mark.asyncio
    async def test_search_chunks_hybrid(self, provider, mock_chunks_ns):
        mock_result = MagicMock()
        mock_result.rows = []
        mock_chunks_ns.query.return_value = mock_result

        filters = ChunkSearchFilters(company_id=1, query_vector=[0.1] * 1536)
        result = await provider.search_chunks(query="test", filters=filters)

        assert len(result.chunks) == 0
        call_kwargs = mock_chunks_ns.query.call_args[1]
        # With query_vector, should use Sum of BM25 + ANN
        rank_by = call_kwargs["rank_by"]
        assert rank_by[0] == "Sum"

    @pytest.mark.asyncio
    async def test_delete_chunk_from_index(self, provider, mock_chunks_ns):
        mock_chunks_ns.write.return_value = MagicMock(rows_affected=1)

        result = await provider.delete_chunk_from_index(
            chunk_id="chunk-1", document_id=10
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_get_supported_filters(self, provider):
        filters = await provider.get_supported_filters()
        assert "content_type" in filters
        assert "extraction_status" in filters
