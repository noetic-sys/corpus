import pytest
import io
from unittest.mock import AsyncMock, patch, MagicMock
from PyPDF2 import PdfReader, PdfWriter

from packages.documents.services.pdf_service import PdfService


@pytest.fixture
def mock_storage():
    """Create a mocked storage service."""
    storage = AsyncMock()
    storage.download = AsyncMock()
    storage.upload = AsyncMock(return_value=True)
    return storage


@pytest.fixture
def mock_markitdown():
    """Create a mocked MarkItDown service."""
    markitdown = MagicMock()
    mock_result = MagicMock()
    mock_result.text_content = "# Test Markdown Content\n\nThis is extracted content."
    markitdown.convert_stream.return_value = mock_result
    return markitdown


@pytest.fixture
def sample_pdf_data():
    """Create a simple PDF with multiple pages for testing."""
    # Create a simple multi-page PDF
    pdf_writer = PdfWriter()

    # Add 3 empty pages for testing
    for i in range(3):
        # Create a simple page (this is just for testing structure)
        _ = pdf_writer.add_blank_page(width=612, height=792)

    # Write to bytes
    pdf_buffer = io.BytesIO()
    pdf_writer.write(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


@pytest.fixture
def pdf_service(mock_storage, mock_markitdown):
    """Create a PdfService instance with mocked dependencies."""
    with patch(
        "packages.documents.services.pdf_service.get_storage", return_value=mock_storage
    ), patch(
        "packages.documents.services.pdf_service.MarkItDown",
        return_value=mock_markitdown,
    ):
        return PdfService()


@patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
@patch("packages.documents.services.pdf_service.settings")
class TestPdfService:
    """Unit tests for PdfService."""

    @pytest.mark.asyncio
    async def test_split_pdf_single_page_per_split(
        self, mock_settings, mock_start_span, pdf_service, mock_storage, sample_pdf_data
    ):
        """Test splitting PDF with 1 page per split (default behavior)."""
        # Setup
        mock_settings.s3_bucket_name = "test-bucket"
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_start_span.return_value.__exit__ = MagicMock(return_value=None)

        mock_storage.download.return_value = sample_pdf_data
        storage_key = "documents/test.pdf"

        # Execute
        result = await pdf_service.split_pdf(storage_key, pages_per_split=1)

        # Verify
        assert len(result) == 3  # Should create 3 single-page PDFs
        assert result[0] == "s3://test-bucket/documents/test_page_1.pdf"
        assert result[1] == "s3://test-bucket/documents/test_page_2.pdf"
        assert result[2] == "s3://test-bucket/documents/test_page_3.pdf"

        # Verify storage calls
        mock_storage.download.assert_called_once_with(storage_key)
        assert mock_storage.upload.call_count == 3

        # Check upload metadata for single pages
        upload_calls = mock_storage.upload.call_args_list
        assert upload_calls[0][1]["metadata"]["page_range"] == "1"
        assert upload_calls[1][1]["metadata"]["page_range"] == "2"
        assert upload_calls[2][1]["metadata"]["page_range"] == "3"

    @pytest.mark.asyncio
    async def test_split_pdf_multiple_pages_per_split(
        self, mock_settings, mock_start_span, pdf_service, mock_storage, sample_pdf_data
    ):
        """Test splitting PDF with multiple pages per split."""
        # Setup
        mock_settings.s3_bucket_name = "test-bucket"
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_start_span.return_value.__exit__ = MagicMock(return_value=None)

        mock_storage.download.return_value = sample_pdf_data
        storage_key = "documents/test.pdf"

        # Execute - split into 2 pages per chunk
        result = await pdf_service.split_pdf(storage_key, pages_per_split=2)

        # Verify
        assert len(result) == 2  # Should create 2 chunks: pages 1-2 and page 3
        assert result[0] == "s3://test-bucket/documents/test_pages_1-2.pdf"
        assert result[1] == "s3://test-bucket/documents/test_pages_3-3.pdf"

        # Verify storage calls
        mock_storage.download.assert_called_once_with(storage_key)
        assert mock_storage.upload.call_count == 2

        # Check upload metadata for multi-page chunks
        upload_calls = mock_storage.upload.call_args_list
        assert upload_calls[0][1]["metadata"]["page_range"] == "1-2"
        assert upload_calls[1][1]["metadata"]["page_range"] == "3-3"

    @pytest.mark.asyncio
    async def test_split_pdf_download_failure(
        self, mock_settings, mock_start_span, pdf_service, mock_storage
    ):
        """Test handling of download failure."""
        # Setup
        mock_settings.s3_bucket_name = "test-bucket"
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_start_span.return_value.__exit__ = MagicMock(return_value=None)

        mock_storage.download.return_value = None  # Simulate download failure
        storage_key = "documents/test.pdf"

        # Execute & Verify
        with pytest.raises(ValueError, match="Failed to download PDF from"):
            await pdf_service.split_pdf(storage_key)

    @pytest.mark.asyncio
    async def test_split_pdf_upload_failure(
        self, mock_settings, mock_start_span, pdf_service, mock_storage, sample_pdf_data
    ):
        """Test handling of upload failure."""
        # Setup
        mock_settings.s3_bucket_name = "test-bucket"
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_start_span.return_value.__exit__ = MagicMock(return_value=None)

        mock_storage.download.return_value = sample_pdf_data
        mock_storage.upload.return_value = False  # Simulate upload failure
        storage_key = "documents/test.pdf"

        # Execute & Verify
        with pytest.raises(Exception, match="Failed to upload chunk"):
            await pdf_service.split_pdf(storage_key)

    @pytest.mark.asyncio
    async def test_convert_page_to_markdown_success(
        self,
        mock_settings,
        mock_start_span,
        pdf_service,
        mock_storage,
        sample_pdf_data,
    ):
        """Test successful conversion of PDF page to markdown."""
        # Setup
        mock_settings.s3_bucket_name = "test-bucket"
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_start_span.return_value.__exit__ = MagicMock(return_value=None)

        mock_storage.download.return_value = sample_pdf_data
        page_url = "s3://test-bucket/documents/test_page_1.pdf"

        # Execute
        result = await pdf_service.convert_page_to_markdown(page_url)

        # Verify
        assert result == "# Test Markdown Content\n\nThis is extracted content."
        mock_storage.download.assert_called_once_with("documents/test_page_1.pdf")
        assert pdf_service.markitdown.convert_stream.called

    @pytest.mark.asyncio
    async def test_convert_page_to_markdown_download_failure(
        self, mock_settings, mock_start_span, pdf_service, mock_storage
    ):
        """Test handling of download failure in markdown conversion."""
        # Setup
        mock_settings.s3_bucket_name = "test-bucket"
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_start_span.return_value.__exit__ = MagicMock(return_value=None)

        mock_storage.download.return_value = None
        page_url = "s3://test-bucket/documents/test_page_1.pdf"

        # Execute & Verify
        with pytest.raises(ValueError, match="Failed to download page PDF from"):
            await pdf_service.convert_page_to_markdown(page_url)

    def test_generate_chunk_key_single_page(
        self, mock_settings, mock_start_span, pdf_service
    ):
        """Test chunk key generation for single pages."""
        base_key = "documents/test"
        chunk_key, page_range = pdf_service._generate_chunk_key(base_key, 0, 1, 1)

        assert chunk_key == "documents/test_page_1.pdf"
        assert page_range == "1"

    def test_generate_chunk_key_multiple_pages(
        self, mock_settings, mock_start_span, pdf_service
    ):
        """Test chunk key generation for multiple pages."""
        base_key = "documents/test"
        chunk_key, page_range = pdf_service._generate_chunk_key(base_key, 0, 3, 3)

        assert chunk_key == "documents/test_pages_1-3.pdf"
        assert page_range == "1-3"

    def test_create_chunk_pdf(
        self, mock_settings, mock_start_span, pdf_service, sample_pdf_data
    ):
        """Test PDF chunk creation."""
        # Create a PDF reader from sample data
        pdf_reader = PdfReader(io.BytesIO(sample_pdf_data))

        # Create a chunk with pages 0-1 (first 2 pages)
        chunk_buffer = pdf_service._create_chunk_pdf(pdf_reader, 0, 2)

        # Verify the chunk is a valid PDF with correct number of pages
        assert isinstance(chunk_buffer, io.BytesIO)
        chunk_reader = PdfReader(chunk_buffer)
        assert len(chunk_reader.pages) == 2
