import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from io import BytesIO
from fastapi import UploadFile

from packages.documents.services.document_service import DocumentService
from packages.documents.models.domain.document import DocumentModel, DocumentCreateModel
from packages.documents.models.database.document import ExtractionStatus
from packages.documents.models.schemas.document import DocumentUploadOptions
from packages.documents.providers.document_search.interface import (
    DocumentSearchResult,
)
from packages.documents.repositories.document_repository import DocumentRepository


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
    """Create a DocumentService instance with mocked storage, bloom filter, and search provider."""
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
        return DocumentService()


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return DocumentModel(
        id=1,
        filename="test.pdf",
        storage_key="documents/test.pdf",
        checksum="a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
        extracted_content_path="extracted/content.txt",
        extraction_status=ExtractionStatus.COMPLETED,
        company_id=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
class TestDocumentSearchProvider:
    """Unit tests for DocumentService search provider integration."""

    @pytest.mark.asyncio
    async def test_search_documents(
        self, mock_start_span, document_service, mock_search_provider, sample_document
    ):
        """Test searching documents through the search provider."""
        # Mock search result
        expected_result = DocumentSearchResult(
            documents=[sample_document], total_count=1, has_more=False
        )
        mock_search_provider.search_documents.return_value = expected_result

        # Call the method
        result = await document_service.search_documents(
            company_id=1,
            query="test query",
            content_type="application/pdf",
            extraction_status="completed",
            created_after="2024-01-01",
            created_before="2024-12-31",
            skip=0,
            limit=10,
        )

        # Assertions
        assert result == expected_result
        mock_search_provider.search_documents.assert_called_once()

        # Verify the filters were passed correctly
        call_args = mock_search_provider.search_documents.call_args
        assert call_args[1]["query"] == "test query"
        assert call_args[1]["skip"] == 0
        assert call_args[1]["limit"] == 10

        filters = call_args[1]["filters"]
        assert filters.company_id == 1
        assert filters.content_type == "application/pdf"
        assert filters.extraction_status == "completed"
        assert filters.created_after == "2024-01-01"
        assert filters.created_before == "2024-12-31"

    @pytest.mark.asyncio
    async def test_list_all_documents(
        self, mock_start_span, document_service, mock_search_provider, sample_document
    ):
        """Test listing all documents through the search provider."""
        # Mock list result
        expected_result = DocumentSearchResult(
            documents=[sample_document], total_count=1, has_more=False
        )
        mock_search_provider.list_documents.return_value = expected_result

        # Call the method
        result = await document_service.list_all_documents(
            company_id=1,
            content_type="application/pdf",
            extraction_status="completed",
            created_after="2024-01-01",
            created_before="2024-12-31",
            skip=0,
            limit=100,
        )

        # Assertions
        assert result == expected_result
        mock_search_provider.list_documents.assert_called_once()

        # Verify the filters were passed correctly
        call_args = mock_search_provider.list_documents.call_args
        assert call_args[1]["skip"] == 0
        assert call_args[1]["limit"] == 100

        filters = call_args[1]["filters"]
        assert filters.company_id == 1
        assert filters.content_type == "application/pdf"
        assert filters.extraction_status == "completed"
        assert filters.created_after == "2024-01-01"
        assert filters.created_before == "2024-12-31"

    @pytest.mark.asyncio
    async def test_upload_document_queues_indexing_job(
        self,
        mock_start_span,
        document_service,
        mock_indexing_job_service,
        mock_storage,
        test_db,
    ):
        """Test that uploading a document queues an indexing job."""
        # Mock the indexing job creation
        mock_indexing_job = AsyncMock()
        mock_indexing_job.id = 1
        mock_indexing_job_service.create_and_queue_job.return_value = mock_indexing_job

        # Create a mock upload file
        file_content = b"test file content"
        file = AsyncMock(spec=UploadFile)
        file.filename = "test.pdf"
        file.content_type = "application/pdf"
        file.size = len(file_content)
        file.file = BytesIO(file_content)
        file.read = AsyncMock(side_effect=[file_content, b""])
        file.seek = AsyncMock()

        # Call the method
        document, is_duplicate = await document_service.upload_document(
            file, company_id=1, options=DocumentUploadOptions()
        )

        # Assertions
        assert not is_duplicate
        assert document.filename == "test.pdf"

        # Verify the document indexing job was queued
        mock_indexing_job_service.create_and_queue_job.assert_called_once()
        call_args = mock_indexing_job_service.create_and_queue_job.call_args[0]
        assert call_args[0] == document.id

    @pytest.mark.asyncio
    async def test_upload_document_indexing_queue_failure_does_not_fail_upload(
        self,
        mock_start_span,
        document_service,
        mock_indexing_job_service,
        mock_storage,
        test_db,
    ):
        """Test that upload continues even if indexing job queue fails."""
        # Mock indexing job service to fail
        mock_indexing_job_service.create_and_queue_job.side_effect = Exception(
            "Queue failed"
        )

        # Create a mock upload file
        file_content = b"test file content"
        file = AsyncMock(spec=UploadFile)
        file.filename = "test.pdf"
        file.content_type = "application/pdf"
        file.size = len(file_content)
        file.file = BytesIO(file_content)
        file.read = AsyncMock(side_effect=[file_content, b""])
        file.seek = AsyncMock()

        # Call the method - should not raise
        document, is_duplicate = await document_service.upload_document(
            file, company_id=1, options=DocumentUploadOptions()
        )

        # Assertions
        assert not is_duplicate
        assert document.filename == "test.pdf"

        # Verify indexing job creation was attempted
        mock_indexing_job_service.create_and_queue_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_duplicate_document_returns_existing(
        self,
        mock_start_span,
        document_service,
        mock_bloom_filter,
        mock_indexing_job_service,
        mock_storage,
        test_db,
    ):
        """Test that uploading a duplicate document returns the existing document."""
        # First upload - create the original document
        file_content = b"test file content"
        file1 = AsyncMock(spec=UploadFile)
        file1.filename = "test.pdf"
        file1.content_type = "application/pdf"
        file1.size = len(file_content)
        file1.file = BytesIO(file_content)
        file1.read = AsyncMock(side_effect=[file_content, b""])
        file1.seek = AsyncMock()

        # Mock indexing job for first upload
        mock_indexing_job = AsyncMock()
        mock_indexing_job.id = 1
        mock_indexing_job_service.create_and_queue_job.return_value = mock_indexing_job

        # First upload should create document
        doc1, is_duplicate1 = await document_service.upload_document(
            file1, company_id=1, options=DocumentUploadOptions()
        )
        assert not is_duplicate1
        assert doc1.filename == "test.pdf"
        original_doc_id = doc1.id

        # Verify storage upload was called
        assert mock_storage.upload.call_count == 1

        # Second upload - same content, should detect duplicate
        file2 = AsyncMock(spec=UploadFile)
        file2.filename = "test_copy.pdf"  # Different filename, same content
        file2.content_type = "application/pdf"
        file2.size = len(file_content)
        file2.file = BytesIO(file_content)
        file2.read = AsyncMock(side_effect=[file_content, b""])
        file2.seek = AsyncMock()

        # Mock bloom filter to indicate it might exist
        mock_bloom_filter.exists.return_value = True

        # Second upload should return existing document
        doc2, is_duplicate2 = await document_service.upload_document(
            file2, company_id=1, options=DocumentUploadOptions()
        )

        # Assertions - MUST return the same document that already exists
        assert is_duplicate2  # Should be marked as duplicate
        assert doc2.id == original_doc_id  # SAME document ID returned
        assert doc2.checksum == doc1.checksum  # Same checksum
        assert doc2.filename == "test.pdf"  # Original filename, not the new one

        # Verify storage upload was NOT called for second upload
        assert (
            mock_storage.upload.call_count == 1
        )  # Still just 1 call from first upload

        # Verify indexing job was only queued once (for first upload)
        assert mock_indexing_job_service.create_and_queue_job.call_count == 1

    @pytest.mark.asyncio
    async def test_upload_same_document_different_companies(
        self,
        mock_start_span,
        document_service,
        mock_bloom_filter,
        mock_indexing_job_service,
        mock_storage,
        test_db,
    ):
        """Test that the same document can be uploaded to different companies."""
        # Same file content
        file_content = b"test file content"

        # Upload to company 1
        file1 = AsyncMock(spec=UploadFile)
        file1.filename = "test.pdf"
        file1.content_type = "application/pdf"
        file1.size = len(file_content)
        file1.file = BytesIO(file_content)
        file1.read = AsyncMock(side_effect=[file_content, b""])
        file1.seek = AsyncMock()

        mock_indexing_job = AsyncMock()
        mock_indexing_job.id = 1
        mock_indexing_job_service.create_and_queue_job.return_value = mock_indexing_job

        doc1, is_duplicate1 = await document_service.upload_document(
            file1, company_id=1, options=DocumentUploadOptions()
        )
        assert not is_duplicate1
        assert doc1.company_id == 1

        # Upload same content to company 2
        file2 = AsyncMock(spec=UploadFile)
        file2.filename = "test.pdf"
        file2.content_type = "application/pdf"
        file2.size = len(file_content)
        file2.file = BytesIO(file_content)
        file2.read = AsyncMock(side_effect=[file_content, b""])
        file2.seek = AsyncMock()

        # Mock bloom filter for company 2 to say it doesn't exist
        mock_bloom_filter.exists.return_value = False

        mock_indexing_job2 = AsyncMock()
        mock_indexing_job2.id = 2
        mock_indexing_job_service.create_and_queue_job.return_value = mock_indexing_job2

        doc2, is_duplicate2 = await document_service.upload_document(
            file2, company_id=2, options=DocumentUploadOptions()
        )

        # Should NOT be duplicate - different company
        assert not is_duplicate2
        assert doc2.company_id == 2
        assert doc2.id != doc1.id  # Different document IDs
        assert doc2.checksum == doc1.checksum  # Same content

        # Both should have been uploaded to storage
        assert mock_storage.upload.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_document_removes_from_search(
        self,
        mock_start_span,
        document_service,
        mock_search_provider,
        mock_storage,
        test_db,
    ):
        """Test that deleting a document removes it from the search index."""
        # Create a document in the database
        doc_repo = DocumentRepository()
        document_create = DocumentCreateModel(
            filename="test.pdf",
            storage_key="documents/test.pdf",
            checksum="test_checksum",
            extraction_status=ExtractionStatus.COMPLETED,
            company_id=1,
        )
        document = await doc_repo.create(document_create)

        # Call delete
        result = await document_service.delete_document(document.id, company_id=1)

        # Assertions
        assert result is True

        # Verify the document was removed from search index
        mock_search_provider.delete_document_from_index.assert_called_once_with(
            document.id
        )

        # Verify it was also deleted from storage
        mock_storage.delete.assert_called_once_with("documents/test.pdf")

    @pytest.mark.asyncio
    async def test_delete_document_continues_if_search_removal_fails(
        self,
        mock_start_span,
        document_service,
        mock_search_provider,
        mock_storage,
        test_db,
    ):
        """Test that document deletion continues even if search index removal fails."""
        # Mock search provider to fail
        mock_search_provider.delete_document_from_index.side_effect = Exception(
            "Index removal failed"
        )

        # Create a document in the database
        doc_repo = DocumentRepository()
        document_create = DocumentCreateModel(
            filename="test.pdf",
            storage_key="documents/test.pdf",
            checksum="test_checksum",
            extraction_status=ExtractionStatus.COMPLETED,
            company_id=1,
        )
        document = await doc_repo.create(document_create)

        # Call delete - should not raise
        result = await document_service.delete_document(document.id, company_id=1)

        # Assertions
        assert result is True

        # Verify index removal was attempted
        mock_search_provider.delete_document_from_index.assert_called_once_with(
            document.id
        )

        # Verify it was still deleted from storage
        mock_storage.delete.assert_called_once_with("documents/test.pdf")

    @pytest.mark.asyncio
    async def test_search_documents_enforces_company_federation(
        self, mock_start_span, document_service, mock_search_provider
    ):
        """Test that search documents always includes company_id in filters for data federation."""
        # Mock search result
        expected_result = DocumentSearchResult(
            documents=[], total_count=0, has_more=False
        )
        mock_search_provider.search_documents.return_value = expected_result

        # Test with different company IDs
        company_ids = [1, 2, 42, 999]

        for company_id in company_ids:
            # Call search with this company_id
            await document_service.search_documents(
                company_id=company_id,
                query="test query",
                skip=0,
                limit=10,
            )

            # Verify the most recent call had the correct company_id
            call_args = mock_search_provider.search_documents.call_args
            filters = call_args[1]["filters"]
            assert (
                filters.company_id == company_id
            ), f"Company ID {company_id} was not properly set in filters"

    @pytest.mark.asyncio
    async def test_list_documents_enforces_company_federation(
        self, mock_start_span, document_service, mock_search_provider
    ):
        """Test that list documents always includes company_id in filters for data federation."""
        # Mock list result
        expected_result = DocumentSearchResult(
            documents=[], total_count=0, has_more=False
        )
        mock_search_provider.list_documents.return_value = expected_result

        # Test with different company IDs
        company_ids = [1, 2, 42, 999]

        for company_id in company_ids:
            # Call list with this company_id
            await document_service.list_all_documents(
                company_id=company_id,
                skip=0,
                limit=100,
            )

            # Verify the most recent call had the correct company_id
            call_args = mock_search_provider.list_documents.call_args
            filters = call_args[1]["filters"]
            assert (
                filters.company_id == company_id
            ), f"Company ID {company_id} was not properly set in filters"
