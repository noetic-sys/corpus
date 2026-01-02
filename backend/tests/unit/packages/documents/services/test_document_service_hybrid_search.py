import pytest
from unittest.mock import AsyncMock, patch

from packages.documents.services.document_service import DocumentService
from packages.documents.models.domain.document_search import (
    HybridDocumentSearchResult,
    MatchType,
)
from packages.documents.providers.document_search.types import (
    ChunkSearchResult,
    ChunkSearchHit,
)
from packages.documents.providers.document_search.interface import DocumentSearchResult
from packages.documents.models.database.document import ExtractionStatus
from packages.documents.repositories.document_repository import DocumentRepository
from packages.documents.models.domain.document import DocumentCreateModel


@pytest.fixture
def mock_storage():
    """Create a mocked storage service."""
    storage = AsyncMock()
    storage.download = AsyncMock()
    storage.upload = AsyncMock(return_value=True)
    storage.delete = AsyncMock()
    return storage


@pytest.fixture
def mock_bloom_filter():
    """Create a mocked bloom filter provider."""
    bloom_filter = AsyncMock()
    bloom_filter.exists = AsyncMock(return_value=False)
    bloom_filter.add = AsyncMock(return_value=True)
    return bloom_filter


@pytest.fixture
def mock_search_provider():
    """Create a mocked document search provider."""
    search_provider = AsyncMock()
    search_provider.index_document = AsyncMock(return_value=True)
    search_provider.delete_document_from_index = AsyncMock(return_value=True)
    search_provider.search_documents = AsyncMock()
    search_provider.list_documents = AsyncMock()
    return search_provider


@pytest.fixture
def mock_indexing_job_service():
    """Create a mocked document indexing job service."""
    indexing_job_service = AsyncMock()
    indexing_job_service.create_and_queue_job = AsyncMock()
    return indexing_job_service


@pytest.fixture
def document_service(
    test_db,
    mock_storage,
    mock_bloom_filter,
    mock_search_provider,
    mock_indexing_job_service,
):
    """Create a DocumentService instance with mocked external providers."""
    with patch(
        "packages.documents.services.document_service.get_storage",
        return_value=mock_storage,
    ), patch(
        "packages.documents.services.document_service.get_bloom_filter_provider",
        return_value=mock_bloom_filter,
    ), patch(
        "packages.documents.services.document_service.get_document_search_provider",
        return_value=mock_search_provider,
    ), patch(
        "packages.documents.services.document_service.DocumentIndexingJobService",
        return_value=mock_indexing_job_service,
    ):
        return DocumentService(test_db)


@patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
class TestHybridDocumentSearch:
    """Unit tests for DocumentService hybrid search functionality."""

    @pytest.mark.asyncio
    async def test_hybrid_search_combines_filename_and_chunk_results(
        self, mock_start_span, document_service, mock_search_provider, sample_document
    ):
        """Test that hybrid search combines filename and chunk search results."""
        # Mock filename search result
        filename_result = DocumentSearchResult(
            documents=[sample_document], total_count=1, has_more=False
        )
        mock_search_provider.search_documents.return_value = filename_result

        # Mock chunk search result
        chunk_hit = ChunkSearchHit(
            chunk_id="chunk_1",
            document_id=sample_document.id,
            company_id=sample_document.company_id,
            content="This is a test chunk content",
            metadata={},
            score=0.85,
        )
        chunk_result = ChunkSearchResult(
            chunks=[chunk_hit], total_count=1, has_more=False
        )

        with patch(
            "packages.documents.services.document_service.get_chunk_search_service"
        ) as mock_get_chunk_service:
            mock_chunk_service = AsyncMock()
            mock_chunk_service.hybrid_search_chunks.return_value = chunk_result
            mock_get_chunk_service.return_value = mock_chunk_service

            # Call hybrid search
            result = await document_service.hybrid_search_documents(
                company_id=sample_document.company_id,
                query="test query",
                skip=0,
                limit=20,
                snippets_per_doc=3,
            )

            # Verify both searches were called
            mock_search_provider.search_documents.assert_called_once()
            mock_chunk_service.hybrid_search_chunks.assert_called_once()

            # Verify result structure
            assert isinstance(result, HybridDocumentSearchResult)
            assert len(result.results) == 1
            assert result.results[0].document.id == sample_document.id
            assert result.results[0].match_type == MatchType.FILENAME_AND_CONTENT
            assert len(result.results[0].snippets) == 1
            assert result.total_count == 1

    @pytest.mark.asyncio
    async def test_hybrid_search_filename_only_match(
        self, mock_start_span, document_service, mock_search_provider, sample_document
    ):
        """Test hybrid search with only filename match (no chunk matches)."""
        # Mock filename search result
        filename_result = DocumentSearchResult(
            documents=[sample_document], total_count=1, has_more=False
        )
        mock_search_provider.search_documents.return_value = filename_result

        # Mock empty chunk search result
        chunk_result = ChunkSearchResult(chunks=[], total_count=0, has_more=False)

        with patch(
            "packages.documents.services.document_service.get_chunk_search_service"
        ) as mock_get_chunk_service:
            mock_chunk_service = AsyncMock()
            mock_chunk_service.hybrid_search_chunks.return_value = chunk_result
            mock_get_chunk_service.return_value = mock_chunk_service

            # Call hybrid search
            result = await document_service.hybrid_search_documents(
                company_id=sample_document.company_id,
                query="test query",
                skip=0,
                limit=20,
                snippets_per_doc=3,
            )

            # Verify result
            assert len(result.results) == 1
            assert result.results[0].match_type == MatchType.FILENAME
            assert len(result.results[0].snippets) == 0
            assert result.results[0].match_score == 1.0

    @pytest.mark.asyncio
    async def test_hybrid_search_content_only_match(
        self, mock_start_span, document_service, mock_search_provider, sample_document
    ):
        """Test hybrid search with only content match (no filename match)."""
        # Mock empty filename search result
        filename_result = DocumentSearchResult(
            documents=[], total_count=0, has_more=False
        )
        mock_search_provider.search_documents.return_value = filename_result

        # Mock chunk search result
        chunk_hit = ChunkSearchHit(
            chunk_id="chunk_1",
            document_id=sample_document.id,
            company_id=sample_document.company_id,
            content="This is a test chunk content",
            metadata={},
            score=0.85,
        )
        chunk_result = ChunkSearchResult(
            chunks=[chunk_hit], total_count=1, has_more=False
        )

        with patch(
            "packages.documents.services.document_service.get_chunk_search_service"
        ) as mock_get_chunk_service:
            mock_chunk_service = AsyncMock()
            mock_chunk_service.hybrid_search_chunks.return_value = chunk_result
            mock_get_chunk_service.return_value = mock_chunk_service

            # Call hybrid search
            result = await document_service.hybrid_search_documents(
                company_id=sample_document.company_id,
                query="test query",
                skip=0,
                limit=20,
                snippets_per_doc=3,
            )

            # Verify result
            assert len(result.results) == 1
            assert result.results[0].match_type == MatchType.HYBRID
            assert len(result.results[0].snippets) == 1
            assert (
                result.results[0].snippets[0].content == "This is a test chunk content"
            )
            assert result.results[0].match_score == 0.85

    @pytest.mark.asyncio
    async def test_hybrid_search_score_boosting_for_combined_match(
        self, mock_start_span, document_service, mock_search_provider, sample_document
    ):
        """Test that documents matching both filename and content get score boost."""
        # Mock filename search result
        filename_result = DocumentSearchResult(
            documents=[sample_document], total_count=1, has_more=False
        )
        mock_search_provider.search_documents.return_value = filename_result

        # Mock chunk search result for same document
        chunk_hit = ChunkSearchHit(
            chunk_id="chunk_1",
            document_id=sample_document.id,
            company_id=sample_document.company_id,
            content="This is a test chunk content",
            metadata={},
            score=0.8,
        )
        chunk_result = ChunkSearchResult(
            chunks=[chunk_hit], total_count=1, has_more=False
        )

        with patch(
            "packages.documents.services.document_service.get_chunk_search_service"
        ) as mock_get_chunk_service:
            mock_chunk_service = AsyncMock()
            mock_chunk_service.hybrid_search_chunks.return_value = chunk_result
            mock_get_chunk_service.return_value = mock_chunk_service

            # Call hybrid search
            result = await document_service.hybrid_search_documents(
                company_id=sample_document.company_id,
                query="test query",
                skip=0,
                limit=20,
                snippets_per_doc=3,
            )

            # Verify score was boosted (0.8 * 1.5 = 1.2)
            assert len(result.results) == 1
            assert result.results[0].match_type == MatchType.FILENAME_AND_CONTENT
            assert abs(result.results[0].match_score - 1.2) < 0.01

    @pytest.mark.asyncio
    async def test_hybrid_search_limits_snippets_per_document(
        self, mock_start_span, document_service, mock_search_provider, sample_document
    ):
        """Test that hybrid search limits snippets per document."""
        # Mock filename search result
        filename_result = DocumentSearchResult(
            documents=[], total_count=0, has_more=False
        )
        mock_search_provider.search_documents.return_value = filename_result

        # Mock chunk search result with multiple chunks for same document
        chunk_hits = [
            ChunkSearchHit(
                chunk_id=f"chunk_{i}",
                document_id=sample_document.id,
                company_id=sample_document.company_id,
                content=f"Test chunk content {i}",
                metadata={},
                score=0.9 - (i * 0.1),
            )
            for i in range(5)
        ]
        chunk_result = ChunkSearchResult(
            chunks=chunk_hits, total_count=5, has_more=False
        )

        with patch(
            "packages.documents.services.document_service.get_chunk_search_service"
        ) as mock_get_chunk_service:
            mock_chunk_service = AsyncMock()
            mock_chunk_service.hybrid_search_chunks.return_value = chunk_result
            mock_get_chunk_service.return_value = mock_chunk_service

            # Call hybrid search with snippets_per_doc=2
            result = await document_service.hybrid_search_documents(
                company_id=sample_document.company_id,
                query="test query",
                skip=0,
                limit=20,
                snippets_per_doc=2,
            )

            # Verify only 2 snippets are returned
            assert len(result.results) == 1
            assert len(result.results[0].snippets) == 2

    @pytest.mark.asyncio
    async def test_hybrid_search_pagination(
        self,
        mock_start_span,
        document_service,
        mock_search_provider,
        sample_company,
        test_db,
    ):
        """Test hybrid search pagination works correctly."""

        # Create multiple documents in DB
        doc_repo = DocumentRepository(test_db)
        documents = []
        for i in range(10):
            doc_create = DocumentCreateModel(
                filename=f"test_{i}.pdf",
                storage_key=f"documents/test_{i}.pdf",
                checksum=f"checksum_{i}",
                extraction_status=ExtractionStatus.COMPLETED,
                company_id=sample_company.id,
            )
            doc = await doc_repo.create(doc_create)
            documents.append(doc)

        # Mock filename search result
        filename_result = DocumentSearchResult(
            documents=documents, total_count=10, has_more=False
        )
        mock_search_provider.search_documents.return_value = filename_result

        # Mock empty chunk search
        chunk_result = ChunkSearchResult(chunks=[], total_count=0, has_more=False)

        with patch(
            "packages.documents.services.document_service.get_chunk_search_service"
        ) as mock_get_chunk_service:
            mock_chunk_service = AsyncMock()
            mock_chunk_service.hybrid_search_chunks.return_value = chunk_result
            mock_get_chunk_service.return_value = mock_chunk_service

            # Call hybrid search with skip=5, limit=3
            result = await document_service.hybrid_search_documents(
                company_id=sample_company.id,
                query="test query",
                skip=5,
                limit=3,
                snippets_per_doc=3,
            )

            # Verify pagination
            assert len(result.results) == 3
            assert result.total_count == 10
            assert result.has_more is True

    @pytest.mark.asyncio
    async def test_hybrid_search_enforces_company_federation(
        self, mock_start_span, document_service, mock_search_provider
    ):
        """Test that hybrid search enforces company_id in filters."""
        # Mock empty results
        filename_result = DocumentSearchResult(
            documents=[], total_count=0, has_more=False
        )
        mock_search_provider.search_documents.return_value = filename_result

        chunk_result = ChunkSearchResult(chunks=[], total_count=0, has_more=False)

        with patch(
            "packages.documents.services.document_service.get_chunk_search_service"
        ) as mock_get_chunk_service:
            mock_chunk_service = AsyncMock()
            mock_chunk_service.hybrid_search_chunks.return_value = chunk_result
            mock_get_chunk_service.return_value = mock_chunk_service

            # Test with specific company_id
            await document_service.hybrid_search_documents(
                company_id=42, query="test query", skip=0, limit=20, snippets_per_doc=3
            )

            # Verify filename search had correct company_id
            call_args = mock_search_provider.search_documents.call_args
            filters = call_args[1]["filters"]
            assert filters.company_id == 42

            # Verify chunk search had correct company_id
            call_args = mock_chunk_service.hybrid_search_chunks.call_args
            filters = call_args[1]["filters"]
            assert filters.company_id == 42
