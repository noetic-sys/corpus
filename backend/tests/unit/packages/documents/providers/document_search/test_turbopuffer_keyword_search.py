import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from packages.documents.providers.document_search.turbopuffer_keyword_search import (
    TurbopufferKeywordSearch,
)
from packages.documents.providers.document_search.types import ChunkSearchFilters


class TestTurbopufferKeywordSearch:
    """Tests for TurbopufferKeywordSearch with mocked Turbopuffer client."""

    @pytest.fixture
    def mock_ns(self):
        ns = MagicMock()
        ns.write = MagicMock()
        ns.query = MagicMock()
        return ns

    @pytest.fixture
    def provider(self, mock_ns):
        with patch(
            "packages.documents.providers.document_search.turbopuffer_keyword_search.turbopuffer"
        ) as mock_tpuf:
            mock_tpuf.Namespace.return_value = mock_ns

            p = TurbopufferKeywordSearch(api_key="test-key")
            yield p

    @pytest.mark.asyncio
    async def test_index_chunk(self, provider, mock_ns):
        mock_ns.write.return_value = MagicMock(rows_affected=1)

        result = await provider.index_chunk(
            chunk_id="chunk-1",
            document_id=10,
            company_id=1,
            content="This is test content for BM25 indexing.",
            metadata={"matrix_id": 5},
        )

        assert result is True
        mock_ns.write.assert_called_once()
        row = mock_ns.write.call_args[1]["upsert_rows"][0]
        assert row["content"] == "This is test content for BM25 indexing."
        assert row["chunk_id"] == "chunk-1"

    @pytest.mark.asyncio
    async def test_index_chunk_failure(self, provider, mock_ns):
        mock_ns.write.side_effect = Exception("API error")

        result = await provider.index_chunk(
            chunk_id="chunk-1",
            document_id=10,
            company_id=1,
            content="content",
            metadata={},
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_index_chunks_bulk(self, provider, mock_ns):
        mock_ns.write.return_value = MagicMock(rows_affected=2)

        chunks = [
            {
                "chunk_id": "chunk-1",
                "document_id": 10,
                "company_id": 1,
                "content": "First chunk content",
                "metadata": {"matrix_id": 5},
            },
            {
                "chunk_id": "chunk-2",
                "document_id": 10,
                "company_id": 1,
                "content": "Second chunk content",
                "metadata": {"matrix_id": 5},
            },
        ]

        result = await provider.index_chunks_bulk(chunks)

        assert result is True
        mock_ns.write.assert_called_once()
        assert len(mock_ns.write.call_args[1]["upsert_rows"]) == 2

    @pytest.mark.asyncio
    async def test_keyword_search_chunks(self, provider, mock_ns):
        mock_row = SimpleNamespace(
            chunk_id="chunk-1",
            document_id=10,
            company_id=1,
            content="The quick brown fox jumps over the lazy dog",
            **{"$dist": 5.2},
        )
        mock_result = MagicMock()
        mock_result.rows = [mock_row]
        mock_ns.query.return_value = mock_result

        filters = ChunkSearchFilters(company_id=1, document_ids=[10])
        result = await provider.keyword_search_chunks(
            query="quick fox",
            filters=filters,
            skip=0,
            limit=10,
        )

        assert len(result.chunks) == 1
        assert result.chunks[0].chunk_id == "chunk-1"

        mock_ns.query.assert_called_once()
        call_kwargs = mock_ns.query.call_args[1]
        assert call_kwargs["top_k"] == 10

    @pytest.mark.asyncio
    async def test_keyword_search_chunks_with_filters(self, provider, mock_ns):
        mock_result = MagicMock()
        mock_result.rows = []
        mock_ns.query.return_value = mock_result

        filters = ChunkSearchFilters(
            company_id=1, document_ids=[10, 20], matrix_id=5, entity_set_id=3
        )
        await provider.keyword_search_chunks(query="test", filters=filters)

        call_kwargs = mock_ns.query.call_args[1]
        tpuf_filters = call_kwargs["filters"]
        # Should be an And filter with 4 conditions
        assert tpuf_filters[0] == "And"
        assert len(tpuf_filters[1]) == 4

    @pytest.mark.asyncio
    async def test_keyword_search_chunks_error(self, provider, mock_ns):
        mock_ns.query.side_effect = Exception("API error")

        filters = ChunkSearchFilters(company_id=1)
        result = await provider.keyword_search_chunks(query="test", filters=filters)

        assert len(result.chunks) == 0
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_delete_chunk_from_index(self, provider, mock_ns):
        mock_ns.write.return_value = MagicMock(rows_affected=1)

        result = await provider.delete_chunk_from_index(
            chunk_id="chunk-1", document_id=10
        )

        assert result is True
        mock_ns.write.assert_called_once()
        assert "10_chunk-1" in mock_ns.write.call_args[1]["deletes"]
