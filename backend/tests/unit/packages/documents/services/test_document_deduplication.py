import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import io
import hashlib

from packages.documents.services.document_service import DocumentService
from packages.documents.models.schemas.document import DocumentUploadOptions
from fastapi import UploadFile


def create_mock_upload_file(content: bytes, filename: str = "test.pdf") -> UploadFile:
    """Helper to create a mock UploadFile."""
    file = io.BytesIO(content)
    upload_file = MagicMock(spec=UploadFile)
    upload_file.filename = filename
    upload_file.content_type = "application/pdf"
    upload_file.size = len(content)
    upload_file.file = file

    # Mock async read method
    async def async_read(size=-1):
        return file.read(size)

    # Mock async seek method
    async def async_seek(offset):
        return file.seek(offset)

    upload_file.read = async_read
    upload_file.seek = async_seek

    return upload_file


@pytest.fixture
def mock_storage():
    """Create a mocked storage service."""
    storage = AsyncMock()
    storage.upload = AsyncMock(return_value=True)
    storage.delete = AsyncMock()
    storage.download = AsyncMock(return_value=b"mock file content")
    storage.exists = AsyncMock(return_value=True)
    storage.list_objects = AsyncMock(return_value=[])
    storage.get_presigned_url = AsyncMock(return_value="https://mock-presigned-url.com")
    storage.get_storage_uri = MagicMock(return_value="s3://mock-bucket/mock-key")
    return storage


@pytest.fixture
def mock_bloom_filter():
    """Create a mocked bloom filter provider."""
    bloom_filter = AsyncMock()
    bloom_filter.exists = AsyncMock(return_value=False)
    bloom_filter.add = AsyncMock(return_value=True)
    return bloom_filter


@pytest.fixture
def document_service(test_db, mock_storage, mock_bloom_filter):
    """Create a DocumentService instance with mocked storage and bloom filter."""
    with patch(
        "packages.documents.services.document_service.get_storage",
        return_value=mock_storage,
    ), patch(
        "packages.documents.services.document_service.get_bloom_filter_provider",
        return_value=mock_bloom_filter,
    ), patch(
        "packages.documents.providers.document_extraction.text_extractor.get_storage",
        return_value=mock_storage,
    ):
        return DocumentService()


@patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
class TestDocumentDeduplication:
    """Unit tests for document deduplication functionality."""

    @pytest.mark.asyncio
    async def test_checksum_calculation(self, mock_start_span, document_service):
        """Test that checksum is calculated correctly for file content."""
        # Create test file content
        content = b"Hello, World!"
        expected_checksum = hashlib.sha256(content).hexdigest()

        upload_file = create_mock_upload_file(content)

        # Calculate checksum
        checksum = await document_service._calculate_checksum_from_stream(upload_file)

        # Verify checksum
        assert checksum == expected_checksum
        # Verify file pointer was reset
        assert upload_file.file.tell() == 0

    @pytest.mark.asyncio
    async def test_checksum_calculation_large_file(
        self, mock_start_span, document_service
    ):
        """Test checksum calculation works with large files in chunks."""
        # Create large test content (100KB)
        content = b"x" * 100000
        expected_checksum = hashlib.sha256(content).hexdigest()

        upload_file = create_mock_upload_file(content)

        # Calculate checksum
        checksum = await document_service._calculate_checksum_from_stream(upload_file)

        # Verify checksum
        assert checksum == expected_checksum
        assert upload_file.file.tell() == 0

    @pytest.mark.asyncio
    async def test_upload_new_document(
        self,
        mock_start_span,
        document_service,
        mock_storage,
        mock_bloom_filter,
        test_db,
    ):
        """Test uploading a new document (not a duplicate)."""
        # Setup
        content = b"Test document content"
        upload_file = create_mock_upload_file(content, "new_document.pdf")

        # Mock bloom filter says it doesn't exist
        mock_bloom_filter.exists.return_value = False

        # Upload document
        document, is_duplicate = await document_service.upload_document(
            upload_file, company_id=1, options=DocumentUploadOptions()
        )

        # Assertions
        assert not is_duplicate
        assert document.filename == "new_document.pdf"
        assert document.checksum == hashlib.sha256(content).hexdigest()
        assert document.storage_key == "documents/company_1/new_document.pdf"

        # Verify bloom filter was checked and updated
        mock_bloom_filter.exists.assert_called_once_with(
            "document_checksums_1", document.checksum
        )
        mock_bloom_filter.add.assert_called_once_with(
            "document_checksums_1", document.checksum
        )

        # Verify storage upload was called
        mock_storage.upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_duplicate_document_bloom_filter_hit(
        self,
        mock_start_span,
        document_service,
        mock_storage,
        mock_bloom_filter,
        test_db,
    ):
        """Test uploading a duplicate document detected by bloom filter."""
        # First, create an existing document
        existing_content = b"Existing document"
        existing_file = create_mock_upload_file(existing_content, "existing.pdf")

        # Upload first document
        mock_bloom_filter.exists.return_value = False
        existing_doc, _ = await document_service.upload_document(
            existing_file, company_id=1, options=DocumentUploadOptions()
        )
        await test_db.commit()

        # Reset mocks
        mock_storage.upload.reset_mock()
        mock_bloom_filter.add.reset_mock()

        # Now try to upload the same content with different filename
        duplicate_file = create_mock_upload_file(existing_content, "duplicate.pdf")

        # Mock bloom filter says it might exist
        mock_bloom_filter.exists.return_value = True

        # Upload duplicate
        document, is_duplicate = await document_service.upload_document(
            duplicate_file, company_id=1, options=DocumentUploadOptions()
        )

        # Assertions
        assert is_duplicate
        assert document.id == existing_doc.id
        assert document.filename == "existing.pdf"  # Original filename
        assert document.checksum == existing_doc.checksum

        # Verify storage upload was NOT called for duplicate
        mock_storage.upload.assert_not_called()

        # Verify bloom filter was NOT updated for duplicate
        mock_bloom_filter.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_document_bloom_filter_false_positive(
        self,
        mock_start_span,
        document_service,
        mock_storage,
        mock_bloom_filter,
        test_db,
    ):
        """Test bloom filter false positive (says exists but doesn't)."""
        content = b"New unique content"
        upload_file = create_mock_upload_file(content, "false_positive.pdf")

        # Mock bloom filter says it might exist (false positive)
        mock_bloom_filter.exists.return_value = True

        # Upload document
        document, is_duplicate = await document_service.upload_document(
            upload_file, company_id=1, options=DocumentUploadOptions()
        )

        # Assertions
        assert not is_duplicate
        assert document.filename == "false_positive.pdf"

        # Verify storage upload was called
        mock_storage.upload.assert_called_once()

        # Verify bloom filter was updated
        mock_bloom_filter.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_multiple_documents_same_checksum(
        self,
        mock_start_span,
        document_service,
        mock_storage,
        mock_bloom_filter,
        test_db,
    ):
        """Test that multiple uploads of same content return the same document."""
        content = b"Shared content"

        # Upload first file
        file1 = create_mock_upload_file(content, "file1.pdf")
        mock_bloom_filter.exists.return_value = False
        doc1, is_dup1 = await document_service.upload_document(
            file1, company_id=1, options=DocumentUploadOptions()
        )
        await test_db.commit()

        # Upload second file with same content
        file2 = create_mock_upload_file(content, "file2.pdf")
        mock_bloom_filter.exists.return_value = True
        doc2, is_dup2 = await document_service.upload_document(
            file2, company_id=1, options=DocumentUploadOptions()
        )

        # Upload third file with same content
        file3 = create_mock_upload_file(content, "file3.pdf")
        mock_bloom_filter.exists.return_value = True
        doc3, is_dup3 = await document_service.upload_document(
            file3, company_id=1, options=DocumentUploadOptions()
        )

        # Assertions
        assert not is_dup1
        assert is_dup2
        assert is_dup3
        assert doc1.id == doc2.id == doc3.id
        assert doc1.checksum == doc2.checksum == doc3.checksum

        # Only one upload should have happened
        assert mock_storage.upload.call_count == 1
        assert mock_bloom_filter.add.call_count == 1

    @pytest.mark.asyncio
    async def test_check_for_duplicate_bloom_negative(
        self, mock_start_span, document_service, mock_bloom_filter
    ):
        """Test _check_for_duplicate when bloom filter says definitely not exists."""
        checksum = "test_checksum"
        mock_bloom_filter.exists.return_value = False

        result = await document_service._check_for_duplicate(checksum, company_id=1)

        assert result is None
        mock_bloom_filter.exists.assert_called_once_with(
            "document_checksums_1", checksum
        )

    @pytest.mark.asyncio
    async def test_empty_file_checksum(self, mock_start_span, document_service):
        """Test checksum calculation for empty file."""
        content = b""
        expected_checksum = hashlib.sha256(content).hexdigest()

        upload_file = create_mock_upload_file(content)

        checksum = await document_service._calculate_checksum_from_stream(upload_file)

        assert checksum == expected_checksum
        assert upload_file.file.tell() == 0
