import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import io
from datetime import datetime

from packages.documents.providers.document_extraction.powerpoint_extractor import (
    PowerPointExtractor,
)
from packages.documents.models.domain.document import DocumentModel


class TestPowerPointExtractor:
    """Unit tests for PowerPoint extractor."""

    @pytest.fixture
    def extractor(self):
        with patch(
            "packages.documents.providers.document_extraction.powerpoint_extractor.get_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_get_storage.return_value = mock_storage
            extractor = PowerPointExtractor()
            return extractor

    @pytest.fixture
    def mock_file_data(self):
        return b"fake powerpoint file data"

    @pytest.fixture
    def mock_document(self):
        return DocumentModel(
            id=1,
            filename="test.pptx",
            storage_key="test_storage_key",
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            file_size=1024,
            checksum="test_checksum",
            company_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def test_supports_file_type_pptx(self, extractor):
        """Test that extractor supports .pptx files."""
        assert (
            extractor.supports_file_type(
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )
            is True
        )

    def test_supports_file_type_case_insensitive(self, extractor):
        """Test that file type checking is case insensitive."""
        assert (
            extractor.supports_file_type(
                "APPLICATION/VND.OPENXMLFORMATS-OFFICEDOCUMENT.PRESENTATIONML.PRESENTATION"
            )
            is True
        )

    def test_does_not_support_unsupported_file_type(self, extractor):
        """Test that extractor rejects unsupported file types."""
        assert extractor.supports_file_type("application/pdf") is False
        assert (
            extractor.supports_file_type(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            is False
        )
        assert (
            extractor.supports_file_type(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            is False
        )
        assert extractor.supports_file_type("text/plain") is False

    async def test_extract_text_success(self, extractor, mock_document, mock_file_data):
        """Test successful text extraction from PowerPoint file."""
        # Setup mocks
        extractor.storage.download = AsyncMock(return_value=mock_file_data)
        mock_result = MagicMock()
        mock_result.text_content = (
            "Slide 1 Title\nSlide 1 Content\nSlide 2 Title\nSlide 2 Content"
        )
        extractor.markitdown.convert_stream = MagicMock(return_value=mock_result)

        # Test
        result = await extractor.extract_text(mock_document)

        # Assertions
        assert (
            result == "Slide 1 Title\nSlide 1 Content\nSlide 2 Title\nSlide 2 Content"
        )
        extractor.storage.download.assert_called_once_with(mock_document.storage_key)
        extractor.markitdown.convert_stream.assert_called_once()
        call_args = extractor.markitdown.convert_stream.call_args
        assert isinstance(call_args[0][0], io.BytesIO)
        # Check that stream_info was passed with correct values
        stream_info = call_args[1]["stream_info"]
        assert stream_info.mimetype == mock_document.content_type
        assert stream_info.extension == ".pptx"
        assert stream_info.filename == mock_document.filename

    async def test_extract_text_empty_content(
        self, extractor, mock_document, mock_file_data
    ):
        """Test text extraction when PowerPoint file has no content."""
        # Setup mocks
        extractor.storage.download = AsyncMock(return_value=mock_file_data)
        mock_result = MagicMock()
        mock_result.text_content = ""
        extractor.markitdown.convert_stream = MagicMock(return_value=mock_result)

        # Test
        result = await extractor.extract_text(mock_document)

        # Assertions
        assert result == ""

    async def test_extract_text_no_result(
        self, extractor, mock_document, mock_file_data
    ):
        """Test text extraction when MarkItDown returns None."""
        # Setup mocks
        extractor.storage.download = AsyncMock(return_value=mock_file_data)
        extractor.markitdown.convert_stream = MagicMock(return_value=None)

        # Test
        result = await extractor.extract_text(mock_document)

        # Assertions
        assert result == ""

    async def test_extract_text_exception(
        self, extractor, mock_document, mock_file_data
    ):
        """Test text extraction when an exception occurs."""
        # Setup mocks
        extractor.storage.download = AsyncMock(return_value=mock_file_data)
        extractor.markitdown.convert_stream = MagicMock(
            side_effect=Exception("Conversion failed")
        )

        # Test
        with pytest.raises(Exception) as exc_info:
            await extractor.extract_text(mock_document)

        assert "Failed to extract text from PowerPoint file" in str(exc_info.value)

    async def test_get_metadata_success(self, extractor, mock_document, mock_file_data):
        """Test successful metadata extraction from PowerPoint file."""
        # Setup mocks
        extractor.storage.download = AsyncMock(return_value=mock_file_data)
        mock_result = MagicMock()
        mock_result.text_content = "Presentation content\nSlide 1\nSlide 2"
        mock_result.title = "Sample Presentation"
        extractor.markitdown.convert_stream = MagicMock(return_value=mock_result)

        # Test
        result = await extractor.get_metadata(mock_document)

        # Assertions
        expected_metadata = {
            "file_size": len(mock_file_data),
            "file_type": mock_document.content_type,
            "extractor": "PowerPointExtractor",
            "title": "Sample Presentation",
            "character_count": len("Presentation content\nSlide 1\nSlide 2"),
            "line_count": 3,
        }
        assert result == expected_metadata

    async def test_get_metadata_no_title(
        self, extractor, mock_document, mock_file_data
    ):
        """Test metadata extraction when PowerPoint file has no title."""
        # Setup mocks
        extractor.storage.download = AsyncMock(return_value=mock_file_data)
        mock_result = MagicMock()
        mock_result.text_content = "Presentation content"
        mock_result.title = None
        extractor.markitdown.convert_stream = MagicMock(return_value=mock_result)

        # Test
        result = await extractor.get_metadata(mock_document)

        # Assertions
        assert "title" not in result
        assert result["character_count"] == len("Presentation content")
        assert result["line_count"] == 1

    async def test_get_metadata_exception(
        self, extractor, mock_document, mock_file_data
    ):
        """Test metadata extraction when an exception occurs."""
        # Setup mocks
        extractor.storage.download = AsyncMock(return_value=mock_file_data)
        extractor.markitdown.convert_stream = MagicMock(
            side_effect=Exception("Metadata extraction failed")
        )

        # Test
        result = await extractor.get_metadata(mock_document)

        # Assertions
        expected_metadata = {
            "file_size": mock_document.file_size,
            "file_type": mock_document.content_type,
            "extractor": "PowerPointExtractor",
            "error": "Metadata extraction failed",
        }
        assert result == expected_metadata
