import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone


from packages.billing.models.domain.usage import QuotaCheck
from packages.documents.services.document_service import DocumentService
from packages.documents.models.domain.document import DocumentModel
from packages.documents.models.database.document import ExtractionStatus


@pytest.fixture
def mock_storage():
    """Create a mocked storage service."""
    storage = AsyncMock()
    storage.download = AsyncMock()
    storage.upload = AsyncMock(return_value=True)
    storage.delete = AsyncMock()
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
def mock_search_provider():
    """Create a mocked document search provider."""
    search_provider = AsyncMock()
    search_provider.index_document = AsyncMock(return_value=True)
    search_provider.delete_document_from_index = AsyncMock(return_value=True)
    search_provider.search_documents = AsyncMock()
    search_provider.list_documents = AsyncMock()
    return search_provider


@pytest.fixture
def mock_quota_service():
    """Create a mocked quota service that allows all operations."""
    quota_service = AsyncMock()
    quota_service.check_storage_quota = AsyncMock(
        return_value=QuotaCheck(
            allowed=True,
            metric_name="storage_bytes",
            current_usage=0,
            limit=1_000_000_000,
            remaining=1_000_000_000,
            percentage_used=0.0,
            warning_threshold_reached=False,
            period_type="monthly",
            period_end=datetime.now(timezone.utc),
        )
    )
    return quota_service


@pytest.fixture
def document_service(
    test_db, mock_storage, mock_bloom_filter, mock_search_provider, mock_quota_service
):
    """Create a DocumentService instance with mocked storage, bloom filter, search provider, and quota service."""
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
        "packages.documents.services.document_service.QuotaService",
        return_value=mock_quota_service,
    ):
        yield DocumentService()


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return DocumentModel(
        id=1,
        company_id=1,
        filename="test.pdf",
        storage_key="documents/test.pdf",
        checksum="a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
        extracted_content_path="extracted/content.txt",
        extraction_status=ExtractionStatus.COMPLETED,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
class TestDocumentService:
    """Unit tests for DocumentService get_extracted_content method."""

    @pytest.mark.asyncio
    async def test_get_extracted_content_success(
        self, mock_start_span, document_service, mock_storage, sample_document
    ):
        """Test successful extraction of content from S3."""
        # Mock successful S3 download
        test_content = "This is the extracted content from the document."
        mock_storage.download.return_value = test_content.encode("utf-8")

        # Call the method
        result = await document_service.get_extracted_content(sample_document)

        # Assertions
        assert result == test_content
        mock_storage.download.assert_called_once_with("extracted/content.txt")

    @pytest.mark.asyncio
    async def test_get_extracted_content_no_path(
        self, mock_start_span, document_service, mock_storage, sample_document
    ):
        """Test when document has no extracted content path."""
        # Remove extracted content path
        sample_document.extracted_content_path = None

        # Call the method
        result = await document_service.get_extracted_content(sample_document)

        # Assertions
        assert result is None
        mock_storage.download.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_extracted_content_wrong_status(
        self, mock_start_span, document_service, mock_storage, sample_document
    ):
        """Test when document extraction status is not COMPLETED."""
        # Set status to PROCESSING
        sample_document.extraction_status = ExtractionStatus.PROCESSING

        # Call the method
        result = await document_service.get_extracted_content(sample_document)

        # Assertions
        assert result is None
        mock_storage.download.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_extracted_content_s3_download_fails(
        self, mock_start_span, document_service, mock_storage, sample_document
    ):
        """Test when S3 download returns None (failure)."""
        # Mock S3 download failure
        mock_storage.download.return_value = None

        # Call the method
        result = await document_service.get_extracted_content(sample_document)

        # Assertions
        assert result is None
        mock_storage.download.assert_called_once_with("extracted/content.txt")

    @pytest.mark.asyncio
    async def test_get_extracted_content_decode_error(
        self, mock_start_span, document_service, mock_storage, sample_document
    ):
        """Test when downloaded bytes cannot be decoded as UTF-8."""
        # Mock S3 download with invalid UTF-8 bytes
        invalid_bytes = b"\x80\x81\x82\x83"  # Invalid UTF-8 sequence
        mock_storage.download.return_value = invalid_bytes

        # Call the method
        result = await document_service.get_extracted_content(sample_document)

        # Assertions
        assert result is None
        mock_storage.download.assert_called_once_with("extracted/content.txt")

    @pytest.mark.asyncio
    async def test_get_extracted_content_storage_exception(
        self, mock_start_span, document_service, mock_storage, sample_document
    ):
        """Test when storage.download raises an exception."""
        # Mock S3 download to raise exception
        mock_storage.download.side_effect = Exception("S3 connection error")

        # Call the method
        result = await document_service.get_extracted_content(sample_document)

        # Assertions
        assert result is None
        mock_storage.download.assert_called_once_with("extracted/content.txt")

    def test_get_file_type_from_document_pdf(self, mock_start_span):
        """Test file type extraction for PDF."""
        document = DocumentModel(
            id=1,
            filename="test.pdf",
            storage_key="test/test.pdf",
            content_type="application/pdf",
            checksum="d665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            company_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        result = DocumentService.get_file_type_from_document(document)
        assert result == "pdf"

    def test_get_file_type_from_document_fallback_to_filename(self, mock_start_span):
        """Test file type extraction falls back to filename extension."""
        document = DocumentModel(
            id=1,
            filename="test.docx",
            storage_key="test/test.docx",
            content_type=None,
            checksum="e665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            company_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        result = DocumentService.get_file_type_from_document(document)
        assert result == "docx"

    def test_get_file_type_from_document_no_extension(self, mock_start_span):
        """Test file type extraction with filename but no extension."""
        document = DocumentModel(
            id=1,
            filename="test",  # No extension
            storage_key="test/test",
            content_type=None,
            checksum="f665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            company_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        result = DocumentService.get_file_type_from_document(document)
        assert result == "test"  # Returns the whole filename when no extension

    def test_get_file_type_from_document_unknown(self, mock_start_span):
        """Test file type extraction with unknown extension."""
        document = DocumentModel(
            id=1,
            filename="test.unknown",
            storage_key="test/unknown",
            content_type=None,
            checksum="f665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            company_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        result = DocumentService.get_file_type_from_document(document)
        assert result == "unknown"

    @pytest.mark.asyncio
    async def test_upload_documents_from_urls_single_text_url(
        self, mock_start_span, document_service, test_db, mock_storage
    ):
        """Test uploading a single text URL."""
        # Mock web search provider to return content
        mock_web_provider = AsyncMock()
        mock_web_provider.get_page_content.return_value = (
            "This is test content from the web page."
        )

        # Mock HEAD request to return text/html
        mock_head_response = AsyncMock()
        mock_head_response.headers = {"content-type": "text/html; charset=utf-8"}

        mock_httpx_client = AsyncMock()
        mock_httpx_client.head.return_value = mock_head_response
        mock_httpx_client.__aenter__.return_value = mock_httpx_client
        mock_httpx_client.__aexit__.return_value = None

        with patch(
            "packages.documents.utils.url_helpers.get_web_search_provider",
            return_value=mock_web_provider,
        ), patch(
            "packages.documents.utils.url_helpers.httpx.AsyncClient",
            return_value=mock_httpx_client,
        ):
            urls = ["https://example.com/page"]
            documents, errors = await document_service.upload_documents_from_urls(
                urls, company_id=1
            )

            # Verify results
            assert len(documents) == 1
            assert len(errors) == 0
            assert documents[0].company_id == 1
            assert "example.com" in documents[0].filename

            # Verify web provider was called
            mock_web_provider.get_page_content.assert_called_once_with(
                "https://example.com/page"
            )

    @pytest.mark.asyncio
    async def test_upload_documents_from_urls_multiple_urls(
        self, mock_start_span, document_service, test_db, mock_storage
    ):
        """Test uploading multiple URLs in parallel."""
        # Mock web search provider for text
        mock_web_provider = AsyncMock()
        mock_web_provider.get_page_content.side_effect = [
            "Content from page 1",
            "Content from page 3",
        ]

        # Mock httpx HEAD and GET requests
        async def mock_httpx_head(url, follow_redirects=True):
            response = AsyncMock()
            if "pdf" in url:
                response.headers = {"content-type": "application/pdf"}
            else:
                response.headers = {"content-type": "text/html"}
            return response

        async def mock_httpx_get(url, follow_redirects=True):
            response = AsyncMock()
            response.content = b"PDF binary content"
            response.headers = {"content-type": "application/pdf"}
            response.raise_for_status = MagicMock()
            return response

        mock_httpx_client = AsyncMock()
        mock_httpx_client.head = mock_httpx_head
        mock_httpx_client.get = mock_httpx_get
        mock_httpx_client.__aenter__.return_value = mock_httpx_client
        mock_httpx_client.__aexit__.return_value = None

        with patch(
            "packages.documents.utils.url_helpers.get_web_search_provider",
            return_value=mock_web_provider,
        ), patch(
            "packages.documents.utils.url_helpers.httpx.AsyncClient",
            return_value=mock_httpx_client,
        ):
            urls = [
                "https://example.com/page1",
                "https://example.com/doc.pdf",
                "https://example.com/page3",
            ]
            documents, errors = await document_service.upload_documents_from_urls(
                urls, company_id=1
            )

            # Verify results
            assert len(documents) == 3
            assert len(errors) == 0

            # Verify all documents have correct company
            for doc in documents:
                assert doc.company_id == 1

    @pytest.mark.asyncio
    async def test_upload_documents_from_urls_with_failures(
        self, mock_start_span, document_service, test_db, mock_storage
    ):
        """Test uploading URLs when some fail to download."""
        # Mock web provider - one success, one failure
        mock_web_provider = AsyncMock()

        async def mock_get_page_side_effect(url):
            if "good" in url:
                return "Good content"
            raise Exception("Failed to fetch page")

        mock_web_provider.get_page_content.side_effect = mock_get_page_side_effect

        # Mock HEAD request to return text/html for both
        mock_head_response = AsyncMock()
        mock_head_response.headers = {"content-type": "text/html"}

        mock_httpx_client = AsyncMock()
        mock_httpx_client.head.return_value = mock_head_response
        mock_httpx_client.__aenter__.return_value = mock_httpx_client
        mock_httpx_client.__aexit__.return_value = None

        with patch(
            "packages.documents.utils.url_helpers.get_web_search_provider",
            return_value=mock_web_provider,
        ), patch(
            "packages.documents.utils.url_helpers.httpx.AsyncClient",
            return_value=mock_httpx_client,
        ):
            urls = ["https://example.com/good", "https://example.com/bad"]
            documents, errors = await document_service.upload_documents_from_urls(
                urls, company_id=1
            )

            # Verify results
            assert len(documents) == 1
            assert len(errors) == 1
            assert "example.com" in documents[0].filename
            assert "bad" in errors[0]

    @pytest.mark.asyncio
    async def test_upload_documents_from_urls_all_fail(
        self, mock_start_span, document_service, test_db, mock_storage
    ):
        """Test uploading URLs when all downloads fail."""
        # Mock web provider to always fail
        mock_web_provider = AsyncMock()
        mock_web_provider.get_page_content.side_effect = Exception("Network error")

        # Mock HEAD request
        mock_head_response = AsyncMock()
        mock_head_response.headers = {"content-type": "text/html"}

        mock_httpx_client = AsyncMock()
        mock_httpx_client.head.return_value = mock_head_response
        mock_httpx_client.__aenter__.return_value = mock_httpx_client
        mock_httpx_client.__aexit__.return_value = None

        with patch(
            "packages.documents.utils.url_helpers.get_web_search_provider",
            return_value=mock_web_provider,
        ), patch(
            "packages.documents.utils.url_helpers.httpx.AsyncClient",
            return_value=mock_httpx_client,
        ):
            urls = [
                "https://example.com/bad1",
                "https://example.com/bad2",
            ]
            documents, errors = await document_service.upload_documents_from_urls(
                urls, company_id=1
            )

            # Verify results
            assert len(documents) == 0
            assert len(errors) == 2

    @pytest.mark.asyncio
    async def test_upload_documents_from_urls_pdf_binary(
        self, mock_start_span, document_service, test_db, mock_storage
    ):
        """Test uploading a PDF URL (binary file)."""
        # Mock HEAD request to return PDF content type
        mock_head_response = AsyncMock()
        mock_head_response.headers = {"content-type": "application/pdf"}

        # Mock GET request for PDF download
        mock_get_response = AsyncMock()
        mock_get_response.content = b"%PDF-1.4 fake pdf content"
        mock_get_response.headers = {"content-type": "application/pdf"}
        mock_get_response.raise_for_status = MagicMock()

        mock_httpx_client = AsyncMock()
        mock_httpx_client.head.return_value = mock_head_response
        mock_httpx_client.get.return_value = mock_get_response
        mock_httpx_client.__aenter__.return_value = mock_httpx_client
        mock_httpx_client.__aexit__.return_value = None

        with patch(
            "packages.documents.utils.url_helpers.httpx.AsyncClient",
            return_value=mock_httpx_client,
        ):
            urls = ["https://example.com/document.pdf"]
            documents, errors = await document_service.upload_documents_from_urls(
                urls, company_id=1
            )

            # Verify results
            assert len(documents) == 1
            assert len(errors) == 0
            assert documents[0].filename == "document.pdf"
            assert documents[0].company_id == 1
            assert documents[0].content_type == "application/pdf"

            # Verify httpx was called for both HEAD and GET
            mock_httpx_client.head.assert_called_once()
            mock_httpx_client.get.assert_called_once_with(
                "https://example.com/document.pdf", follow_redirects=True
            )

    @pytest.mark.asyncio
    async def test_upload_documents_from_urls_mixed_text_and_binary(
        self, mock_start_span, document_service, test_db, mock_storage
    ):
        """Test uploading mix of text URLs and binary URLs."""
        # Mock web search provider for text
        mock_web_provider = AsyncMock()
        mock_web_provider.get_page_content.return_value = "Text content from webpage"

        # Mock httpx HEAD to return proper content types
        async def mock_httpx_head(url, follow_redirects=True):
            response = AsyncMock()
            if "pdf" in url:
                response.headers = {"content-type": "application/pdf"}
            elif "xlsx" in url:
                response.headers = {
                    "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                }
            else:
                response.headers = {"content-type": "text/html"}
            return response

        # Mock httpx GET for binary files - different content for each to avoid deduplication
        async def mock_httpx_get(url, follow_redirects=True):
            response = AsyncMock()
            if "pdf" in url:
                response.content = b"%PDF-1.4 pdf binary content"
                response.headers = {"content-type": "application/pdf"}
            elif "xlsx" in url:
                response.content = b"PK excel binary content different"
                response.headers = {
                    "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                }
            response.raise_for_status = MagicMock()
            return response

        mock_httpx_client = AsyncMock()
        mock_httpx_client.head = mock_httpx_head
        mock_httpx_client.get = mock_httpx_get
        mock_httpx_client.__aenter__.return_value = mock_httpx_client
        mock_httpx_client.__aexit__.return_value = None

        with patch(
            "packages.documents.utils.url_helpers.get_web_search_provider",
            return_value=mock_web_provider,
        ), patch(
            "packages.documents.utils.url_helpers.httpx.AsyncClient",
            return_value=mock_httpx_client,
        ):
            urls = [
                "https://example.com/article",  # Text page
                "https://example.com/report.pdf",  # Binary PDF
                "https://example.com/data.xlsx",  # Binary Excel
            ]
            documents, errors = await document_service.upload_documents_from_urls(
                urls, company_id=1
            )

            # Verify results
            assert len(documents) == 3
            assert len(errors) == 0

            # Verify we have text and binary documents
            filenames = [d.filename for d in documents]
            assert any(".txt" in f or "article" in f for f in filenames)
            assert "report.pdf" in filenames
            assert "data.xlsx" in filenames

            # Verify text URL used Exa
            mock_web_provider.get_page_content.assert_called_once_with(
                "https://example.com/article"
            )


@patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
class TestUrlUploadQuotaEnforcement:
    """Tests for quota enforcement on URL uploads with actual file size."""

    @pytest.mark.asyncio
    async def test_url_upload_blocked_when_actual_file_size_exceeds_quota(
        self,
        mock_start_span,
        test_db,
        mock_storage,
        mock_bloom_filter,
        mock_search_provider,
    ):
        """Test that URL upload is blocked when actual file size would exceed storage quota."""
        # Mock quota service to reject based on file size
        mock_quota_service = AsyncMock()
        mock_quota_service.check_storage_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=False,
                metric_name="storage_bytes",
                current_usage=990_000_000,
                limit=1_000_000_000,
                remaining=10_000_000,
                percentage_used=99.0,
                warning_threshold_reached=True,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )

        # Mock HEAD request to return PDF content type
        mock_head_response = AsyncMock()
        mock_head_response.headers = {"content-type": "application/pdf"}

        # Mock GET request for PDF download - large file
        mock_get_response = AsyncMock()
        mock_get_response.content = b"%PDF-1.4 " + (b"x" * 50_000_000)  # 50MB file
        mock_get_response.headers = {"content-type": "application/pdf"}
        mock_get_response.raise_for_status = MagicMock()

        mock_httpx_client = AsyncMock()
        mock_httpx_client.head.return_value = mock_head_response
        mock_httpx_client.get.return_value = mock_get_response
        mock_httpx_client.__aenter__.return_value = mock_httpx_client
        mock_httpx_client.__aexit__.return_value = None

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
            "packages.documents.services.document_service.QuotaService",
            return_value=mock_quota_service,
        ), patch(
            "packages.documents.utils.url_helpers.httpx.AsyncClient",
            return_value=mock_httpx_client,
        ):
            document_service = DocumentService()
            urls = ["https://example.com/large-document.pdf"]

            # Should include error for the file that exceeded quota
            documents, errors = await document_service.upload_documents_from_urls(
                urls, company_id=1
            )

            # Verify the upload was rejected due to quota
            assert len(documents) == 0
            assert len(errors) == 1
            assert any(
                word in errors[0].lower()
                for word in ["quota", "limit", "storage", "402"]
            )

            # Verify quota was checked with actual file size
            mock_quota_service.check_storage_quota.assert_called()
            call_kwargs = mock_quota_service.check_storage_quota.call_args.kwargs
            assert call_kwargs["company_id"] == 1
            # File size should be > 0 (actual file size, not the 0 from route-level check)
            assert call_kwargs["file_size_bytes"] > 0

    @pytest.mark.asyncio
    async def test_url_upload_allowed_when_quota_available(
        self,
        mock_start_span,
        test_db,
        mock_storage,
        mock_bloom_filter,
        mock_search_provider,
    ):
        """Test that URL upload succeeds when storage quota is available."""
        # Mock quota service to allow upload
        mock_quota_service = AsyncMock()
        mock_quota_service.check_storage_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=True,
                metric_name="storage_bytes",
                current_usage=100_000_000,
                limit=1_000_000_000,
                remaining=900_000_000,
                percentage_used=10.0,
                warning_threshold_reached=False,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )

        # Mock HEAD request to return PDF content type
        mock_head_response = AsyncMock()
        mock_head_response.headers = {"content-type": "application/pdf"}

        # Mock GET request for PDF download
        mock_get_response = AsyncMock()
        mock_get_response.content = b"%PDF-1.4 small pdf content"
        mock_get_response.headers = {"content-type": "application/pdf"}
        mock_get_response.raise_for_status = MagicMock()

        mock_httpx_client = AsyncMock()
        mock_httpx_client.head.return_value = mock_head_response
        mock_httpx_client.get.return_value = mock_get_response
        mock_httpx_client.__aenter__.return_value = mock_httpx_client
        mock_httpx_client.__aexit__.return_value = None

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
            "packages.documents.services.document_service.QuotaService",
            return_value=mock_quota_service,
        ), patch(
            "packages.documents.utils.url_helpers.httpx.AsyncClient",
            return_value=mock_httpx_client,
        ):
            document_service = DocumentService()
            urls = ["https://example.com/small-document.pdf"]

            documents, errors = await document_service.upload_documents_from_urls(
                urls, company_id=1
            )

            # Verify upload succeeded
            assert len(documents) == 1
            assert len(errors) == 0
            assert documents[0].filename == "small-document.pdf"

            # Verify quota was checked with actual file size
            mock_quota_service.check_storage_quota.assert_called()
            call_kwargs = mock_quota_service.check_storage_quota.call_args.kwargs
            assert call_kwargs["file_size_bytes"] > 0
