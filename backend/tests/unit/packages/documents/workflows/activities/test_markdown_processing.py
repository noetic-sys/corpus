import pytest
from unittest.mock import AsyncMock, patch
import io
from typing import List

from packages.documents.workflows.activities.markdown_processing import (
    combine_markdown_activity,
    save_markdown_to_s3_activity,
)
from packages.documents.workflows.common import MarkdownPage


@patch(
    "packages.documents.workflows.activities.markdown_processing.create_span_with_context"
)
class TestCombineMarkdownActivity:
    """Unit tests for combine_markdown_activity."""

    @pytest.mark.asyncio
    async def test_combine_markdown_single_page(self, mock_create_span):
        """Test combining a single markdown page."""

        # Create test pages
        pages = [MarkdownPage(page_number=0, content="# Page 1\nContent of page 1")]

        # Call the activity
        result = await combine_markdown_activity(pages, {"trace-id": "12345"})

        # Assertions
        assert result == "# Page 1\nContent of page 1"
        mock_create_span.assert_called_once_with(
            "temporal::combine_markdown_activity", {"trace-id": "12345"}
        )

    @pytest.mark.asyncio
    async def test_combine_markdown_multiple_pages(self, mock_create_span):
        """Test combining multiple markdown pages."""

        # Create test pages
        pages = [
            MarkdownPage(page_number=0, content="# Page 1\nContent of page 1"),
            MarkdownPage(page_number=1, content="# Page 2\nContent of page 2"),
            MarkdownPage(page_number=2, content="# Page 3\nContent of page 3"),
        ]

        # Call the activity
        result = await combine_markdown_activity(pages)

        # Assertions
        expected = "# Page 1\nContent of page 1\n\n---\n\n# Page 2\nContent of page 2\n\n---\n\n# Page 3\nContent of page 3"
        assert result == expected
        mock_create_span.assert_called_once_with(
            "temporal::combine_markdown_activity", None
        )

    @pytest.mark.asyncio
    async def test_combine_markdown_empty_list(self, mock_create_span):
        """Test combining empty list of pages."""

        # Create empty pages list
        pages: List[MarkdownPage] = []

        # Call the activity
        result = await combine_markdown_activity(pages)

        # Assertions
        assert result == ""
        mock_create_span.assert_called_once_with(
            "temporal::combine_markdown_activity", None
        )

    @pytest.mark.asyncio
    async def test_combine_markdown_with_special_characters(self, mock_create_span):
        """Test combining pages with special characters and formatting."""

        # Create test pages with special characters
        pages = [
            MarkdownPage(
                page_number=0,
                content="# Título con acentos\n**Bold text** and *italic*",
            ),
            MarkdownPage(
                page_number=1, content="## Code block\n```python\nprint('hello')\n```"
            ),
            MarkdownPage(
                page_number=2,
                content="### Links and images\n[Link](http://example.com)\n![Image](image.png)",
            ),
        ]

        # Call the activity
        result = await combine_markdown_activity(pages)

        # Assertions
        expected = (
            "# Título con acentos\n**Bold text** and *italic*\n\n---\n\n"
            "## Code block\n```python\nprint('hello')\n```\n\n---\n\n"
            "### Links and images\n[Link](http://example.com)\n![Image](image.png)"
        )
        assert result == expected

    @pytest.mark.asyncio
    async def test_combine_markdown_with_blank_pages(self, mock_create_span):
        """Test combining pages where some pages are blank (empty content)."""

        # Create test pages with blank pages mixed in
        pages = [
            MarkdownPage(page_number=0, content="# Page 1\nContent on first page"),
            MarkdownPage(page_number=1, content=""),  # Blank page
            MarkdownPage(page_number=2, content="# Page 3\nContent on third page"),
            MarkdownPage(page_number=3, content=""),  # Another blank page
            MarkdownPage(page_number=4, content="# Page 5\nContent on fifth page"),
        ]

        # Call the activity
        result = await combine_markdown_activity(pages)

        # Assertions - blank pages should still be included with separators
        expected = "# Page 1\nContent on first page\n\n---\n\n\n\n---\n\n# Page 3\nContent on third page\n\n---\n\n\n\n---\n\n# Page 5\nContent on fifth page"
        assert result == expected
        mock_create_span.assert_called_once_with(
            "temporal::combine_markdown_activity", None
        )

    @pytest.mark.asyncio
    async def test_combine_markdown_all_blank_pages(self, mock_create_span):
        """Test combining pages where all pages are blank."""

        # Create test pages that are all blank
        pages = [
            MarkdownPage(page_number=0, content=""),
            MarkdownPage(page_number=1, content=""),
            MarkdownPage(page_number=2, content=""),
        ]

        # Call the activity
        result = await combine_markdown_activity(pages)

        # Assertions - should have separators but no content
        expected = "\n\n---\n\n\n\n---\n\n"
        assert result == expected
        mock_create_span.assert_called_once_with(
            "temporal::combine_markdown_activity", None
        )

    @pytest.mark.asyncio
    async def test_markdown_page_model_allows_blank_content(self, mock_create_span):
        """Test that MarkdownPage model accepts blank/empty content."""

        # This should NOT raise a validation error
        blank_page = MarkdownPage(page_number=5, content="")

        assert blank_page.page_number == 5
        assert blank_page.content == ""

        # Also test with explicit empty string
        another_blank = MarkdownPage(page_number=10, content="")
        assert another_blank.content == ""


@patch(
    "packages.documents.workflows.activities.markdown_processing.create_span_with_context"
)
@patch("packages.documents.workflows.activities.markdown_processing.get_storage")
class TestSaveMarkdownToS3Activity:
    """Unit tests for save_markdown_to_s3_activity."""

    @pytest.mark.asyncio
    async def test_save_markdown_success(
        self,
        mock_get_storage,
        mock_create_span,
        test_db,
        sample_document,
        sample_company,
    ):
        """Test successful saving of markdown content to S3."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Mock storage provider
        mock_storage = AsyncMock()
        mock_storage.upload.return_value = True
        mock_get_storage.return_value = mock_storage

        # Test data
        markdown_content = "# Document Title\nThis is some markdown content."

        # Call the activity
        result = await save_markdown_to_s3_activity(
            markdown_content, sample_document.id, {"trace-id": "12345"}
        )

        # Assertions - path now includes company_id
        expected_s3_key = (
            f"company/{sample_company.id}/documents/{sample_document.id}/extracted.md"
        )
        assert result == expected_s3_key

        # Verify upload was called with correct parameters
        mock_storage.upload.assert_called_once()
        call_args = mock_storage.upload.call_args
        assert call_args[0][0] == expected_s3_key  # s3_key
        assert isinstance(call_args[0][1], io.BytesIO)  # content stream
        assert call_args[1]["metadata"]["content_type"] == "text/markdown"

        # Verify the content was encoded correctly
        uploaded_content = call_args[0][1].getvalue()
        assert uploaded_content == markdown_content.encode("utf-8")

        mock_create_span.assert_called_once_with(
            "temporal::save_markdown_to_s3_activity", {"trace-id": "12345"}
        )

    @pytest.mark.asyncio
    async def test_save_markdown_upload_failure(
        self, mock_get_storage, mock_create_span, test_db, sample_document
    ):
        """Test when S3 upload returns False (failure)."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Mock storage provider to return False (upload failure)
        mock_storage = AsyncMock()
        mock_storage.upload.return_value = False
        mock_get_storage.return_value = mock_storage

        # Test data
        markdown_content = "# Document Title\nThis is some markdown content."

        # Call the activity and expect exception
        with pytest.raises(Exception, match="Failed to upload markdown to S3"):
            await save_markdown_to_s3_activity(markdown_content, sample_document.id)

        # Verify upload was attempted
        mock_storage.upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_markdown_storage_exception(
        self, mock_get_storage, mock_create_span, test_db, sample_document
    ):
        """Test when storage upload raises an exception."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Mock storage provider to raise exception
        mock_storage = AsyncMock()
        mock_storage.upload.side_effect = Exception("S3 connection failed")
        mock_get_storage.return_value = mock_storage

        # Test data
        markdown_content = "# Document Title\nThis is some markdown content."

        # Call the activity and expect exception to propagate
        with pytest.raises(Exception, match="S3 connection failed"):
            await save_markdown_to_s3_activity(markdown_content, sample_document.id)

        # Verify upload was attempted
        mock_storage.upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_markdown_no_trace_headers(
        self,
        mock_get_storage,
        mock_create_span,
        test_db,
        sample_document,
        sample_company,
    ):
        """Test saving markdown without trace headers."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Mock storage provider
        mock_storage = AsyncMock()
        mock_storage.upload.return_value = True
        mock_get_storage.return_value = mock_storage

        # Test data
        markdown_content = "# Document Title\nThis is some markdown content."

        # Call the activity without trace headers
        result = await save_markdown_to_s3_activity(
            markdown_content, sample_document.id
        )

        # Assertions - path now includes company_id
        expected_s3_key = (
            f"company/{sample_company.id}/documents/{sample_document.id}/extracted.md"
        )
        assert result == expected_s3_key
        mock_create_span.assert_called_once_with(
            "temporal::save_markdown_to_s3_activity", None
        )

    @pytest.mark.asyncio
    async def test_save_markdown_unicode_content(
        self,
        mock_get_storage,
        mock_create_span,
        test_db,
        sample_document,
        sample_company,
    ):
        """Test saving markdown with unicode characters."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Mock storage provider
        mock_storage = AsyncMock()
        mock_storage.upload.return_value = True
        mock_get_storage.return_value = mock_storage

        # Test data with unicode characters
        markdown_content = "# Título con acentos\n这是中文内容\n🚀 Emoji content"

        # Call the activity
        result = await save_markdown_to_s3_activity(
            markdown_content, sample_document.id
        )

        # Assertions - path now includes company_id
        expected_s3_key = (
            f"company/{sample_company.id}/documents/{sample_document.id}/extracted.md"
        )
        assert result == expected_s3_key

        # Verify the unicode content was encoded correctly
        call_args = mock_storage.upload.call_args
        uploaded_content = call_args[0][1].getvalue()
        assert uploaded_content == markdown_content.encode("utf-8")

    @pytest.mark.asyncio
    async def test_save_markdown_empty_content(
        self,
        mock_get_storage,
        mock_create_span,
        test_db,
        sample_document,
        sample_company,
    ):
        """Test saving empty markdown content."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Mock storage provider
        mock_storage = AsyncMock()
        mock_storage.upload.return_value = True
        mock_get_storage.return_value = mock_storage

        # Test data
        markdown_content = ""

        # Call the activity
        result = await save_markdown_to_s3_activity(
            markdown_content, sample_document.id
        )

        # Assertions - path now includes company_id
        expected_s3_key = (
            f"company/{sample_company.id}/documents/{sample_document.id}/extracted.md"
        )
        assert result == expected_s3_key

        # Verify empty content was handled correctly
        call_args = mock_storage.upload.call_args
        uploaded_content = call_args[0][1].getvalue()
        assert uploaded_content == b""
