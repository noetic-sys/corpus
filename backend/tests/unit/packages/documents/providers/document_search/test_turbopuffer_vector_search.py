import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from packages.documents.providers.document_search.turbopuffer_vector_search import (
    TurbopufferVectorSearch,
)
from packages.documents.providers.document_search.types import ChunkSearchFilters


class TestTurbopufferVectorSearch:
    """Tests for TurbopufferVectorSearch with mocked Turbopuffer client."""

    @pytest.fixture
    def mock_ns(self):
        ns = MagicMock()
        ns.write = MagicMock()
        ns.query = MagicMock()
        return ns

    @pytest.fixture
    def provider(self, mock_ns):
        with patch(
            "packages.documents.providers.document_search.turbopuffer_vector_search.turbopuffer"
        ) as mock_tpuf:
            mock_tpuf.Namespace.return_value = mock_ns

            p = TurbopufferVectorSearch(api_key="test-key", embedding_dim=1536)
            yield p

    @pytest.mark.asyncio
    async def test_index_chunk_embedding(self, provider, mock_ns):
        mock_ns.write.return_value = MagicMock(rows_affected=1)

        result = await provider.index_chunk_embedding(
            chunk_id="chunk-1",
            document_id=10,
            company_id=1,
            embedding=[0.1] * 1536,
            metadata={"matrix_id": 5, "entity_set_id": 3},
        )

        assert result is True
        mock_ns.write.assert_called_once()
        call_kwargs = mock_ns.write.call_args[1]
        assert len(call_kwargs["upsert_rows"]) == 1
        row = call_kwargs["upsert_rows"][0]
        assert row["id"] == "10_chunk-1"
        assert row["chunk_id"] == "chunk-1"
        assert row["company_id"] == 1
        assert call_kwargs["distance_metric"] == "cosine_distance"

    @pytest.mark.asyncio
    async def test_index_chunk_embedding_failure(self, provider, mock_ns):
        mock_ns.write.side_effect = Exception("API error")

        result = await provider.index_chunk_embedding(
            chunk_id="chunk-1",
            document_id=10,
            company_id=1,
            embedding=[0.1] * 1536,
            metadata={},
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_index_embeddings_bulk(self, provider, mock_ns):
        mock_ns.write.return_value = MagicMock(rows_affected=2)

        embeddings = [
            {
                "chunk_id": "chunk-1",
                "document_id": 10,
                "company_id": 1,
                "embedding": [0.1] * 1536,
                "metadata": {"matrix_id": 5},
            },
            {
                "chunk_id": "chunk-2",
                "document_id": 10,
                "company_id": 1,
                "embedding": [0.2] * 1536,
                "metadata": {"matrix_id": 5},
            },
        ]

        result = await provider.index_embeddings_bulk(embeddings)

        assert result is True
        mock_ns.write.assert_called_once()
        call_kwargs = mock_ns.write.call_args[1]
        assert len(call_kwargs["upsert_rows"]) == 2

    @pytest.mark.asyncio
    async def test_vector_search_chunks(self, provider, mock_ns):
        mock_row = SimpleNamespace(
            chunk_id="chunk-1",
            document_id=10,
            company_id=1,
            **{"$dist": 0.95},
        )
        mock_result = MagicMock()
        mock_result.rows = [mock_row]
        mock_ns.query.return_value = mock_result

        filters = ChunkSearchFilters(company_id=1, document_ids=[10])
        result = await provider.vector_search_chunks(
            query_vector=[0.1] * 1536,
            filters=filters,
            skip=0,
            limit=10,
        )

        assert len(result.chunks) == 1
        assert result.chunks[0].chunk_id == "chunk-1"
        assert result.chunks[0].document_id == 10

        mock_ns.query.assert_called_once()
        call_kwargs = mock_ns.query.call_args[1]
        assert call_kwargs["top_k"] == 10
        assert call_kwargs["include_attributes"] is True

    @pytest.mark.asyncio
    async def test_vector_search_chunks_empty(self, provider, mock_ns):
        mock_result = MagicMock()
        mock_result.rows = []
        mock_ns.query.return_value = mock_result

        filters = ChunkSearchFilters(company_id=1)
        result = await provider.vector_search_chunks(
            query_vector=[0.1] * 1536,
            filters=filters,
        )

        assert len(result.chunks) == 0
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_vector_search_chunks_error(self, provider, mock_ns):
        mock_ns.query.side_effect = Exception("API error")

        filters = ChunkSearchFilters(company_id=1)
        result = await provider.vector_search_chunks(
            query_vector=[0.1] * 1536,
            filters=filters,
        )

        assert len(result.chunks) == 0
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_delete_chunk_embedding(self, provider, mock_ns):
        mock_ns.write.return_value = MagicMock(rows_affected=1)

        result = await provider.delete_chunk_embedding(
            chunk_id="chunk-1", document_id=10
        )

        assert result is True
        mock_ns.write.assert_called_once()
        call_kwargs = mock_ns.write.call_args[1]
        assert "10_chunk-1" in call_kwargs["deletes"]

    def test_get_embedding_dimension(self, provider):
        assert provider.get_embedding_dimension() == 1536
