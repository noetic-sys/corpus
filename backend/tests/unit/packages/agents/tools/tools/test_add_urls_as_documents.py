import pytest
from unittest.mock import AsyncMock, patch
from pydantic import HttpUrl

from packages.agents.tools.base import ToolPermission, ToolContext
from packages.agents.tools.tools.add_urls_as_documents import (
    AddUrlsAsDocumentsTool,
    AddUrlsAsDocumentsParameters,
)
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.documents.models.schemas.document import (
    BulkUrlUploadResponse,
    DocumentResponse,
)
from datetime import datetime


class TestAddUrlsAsDocumentsTool:
    """Test AddUrlsAsDocumentsTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return AddUrlsAsDocumentsTool()

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return AuthenticatedUser(company_id=1, user_id=1)

    def test_tool_definition(self):
        """Test tool definition is correctly configured."""
        definition = AddUrlsAsDocumentsTool.definition()

        assert definition.name == "add_urls_as_documents"
        assert "Fetch content from multiple URLs in parallel" in definition.description
        assert "properties" in definition.parameters
        assert "matrix_id" in definition.parameters["properties"]
        assert "entity_set_id" in definition.parameters["properties"]
        assert "urls" in definition.parameters["properties"]

    def test_permissions(self):
        """Test tool has correct permissions."""
        permissions = AddUrlsAsDocumentsTool.permissions()
        assert permissions == ToolPermission.WRITE

    def test_allowed_contexts(self):
        """Test tool is allowed in correct contexts."""
        contexts = AddUrlsAsDocumentsTool.allowed_contexts()
        assert ToolContext.GENERAL_AGENT in contexts
        assert ToolContext.WORKFLOW_AGENT not in contexts

    def test_parameter_class(self):
        """Test parameter class is correctly configured."""
        param_class = AddUrlsAsDocumentsTool.parameter_class()
        assert param_class == AddUrlsAsDocumentsParameters

    def test_parameters_validation(self):
        """Test parameter validation."""
        # Valid parameters with single URL
        params = AddUrlsAsDocumentsParameters(
            matrix_id=123,
            entity_set_id=10,
            urls=[HttpUrl("https://example.com/page1")],
        )
        assert params.matrix_id == 123
        assert params.entity_set_id == 10
        assert len(params.urls) == 1

        # Valid parameters with multiple URLs
        params_multi = AddUrlsAsDocumentsParameters(
            matrix_id=456,
            entity_set_id=20,
            urls=[
                HttpUrl("https://example.com/page1"),
                HttpUrl("https://example.com/page2.pdf"),
                HttpUrl("https://example.com/page3"),
            ],
        )
        assert params_multi.matrix_id == 456
        assert params_multi.entity_set_id == 20
        assert len(params_multi.urls) == 3

        # Invalid parameters should raise validation error
        with pytest.raises(ValueError):
            AddUrlsAsDocumentsParameters(
                matrix_id=123, entity_set_id=10
            )  # Missing required urls

    async def test_execute_single_url_success(self, tool, mock_user):
        """Test successful tool execution with single URL."""
        mock_session = AsyncMock()

        # Mock successful response
        mock_doc = DocumentResponse(
            id=1,
            company_id=1,
            filename="example.com_page1.txt",
            storage_key="documents/company_1/example.com_page1.txt",
            checksum="abc123",
            content_type="text/plain",
            file_size=1024,
            extraction_status="pending",
            extracted_content_path=None,
            extraction_started_at=None,
            extraction_completed_at=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_response = BulkUrlUploadResponse(documents=[mock_doc], errors=[])

        # Mock the upload_documents_from_urls route
        with patch(
            "packages.agents.tools.tools.add_urls_as_documents.upload_documents_from_urls"
        ) as mock_upload:
            mock_upload.return_value = mock_response

            # Execute tool
            params = AddUrlsAsDocumentsParameters(
                matrix_id=123,
                entity_set_id=10,
                urls=[HttpUrl("https://example.com/page1")],
            )
            result = await tool.execute(params, mock_session, mock_user)

            # Verify result
            assert result.error is None
            assert result.result is not None
            assert len(result.result.documents) == 1
            assert result.result.documents[0].id == 1
            assert result.result.documents[0].filename == "example.com_page1.txt"
            assert len(result.result.errors) == 0

            # Verify route was called correctly
            mock_upload.assert_called_once()
            call_kwargs = mock_upload.call_args[1]
            assert call_kwargs["matrix_id"] == 123
            assert call_kwargs["entity_set_id"] == 10
            assert call_kwargs["current_user"] == mock_user
            assert call_kwargs["db"] == mock_session

    async def test_execute_multiple_urls_success(self, tool, mock_user):
        """Test successful tool execution with multiple URLs."""
        mock_session = AsyncMock()

        # Mock successful response with multiple documents
        mock_docs = [
            DocumentResponse(
                id=i,
                company_id=1,
                filename=f"doc{i}.txt",
                storage_key=f"documents/company_1/doc{i}.txt",
                checksum=f"checksum{i}",
                content_type="text/plain",
                file_size=1024,
                extraction_status="pending",
                extracted_content_path=None,
                extraction_started_at=None,
                extraction_completed_at=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            for i in range(1, 4)
        ]
        mock_response = BulkUrlUploadResponse(documents=mock_docs, errors=[])

        with patch(
            "packages.agents.tools.tools.add_urls_as_documents.upload_documents_from_urls"
        ) as mock_upload:
            mock_upload.return_value = mock_response

            # Execute tool with multiple URLs
            params = AddUrlsAsDocumentsParameters(
                matrix_id=123,
                entity_set_id=10,
                urls=[
                    HttpUrl("https://example.com/page1"),
                    HttpUrl("https://example.com/page2"),
                    HttpUrl("https://example.com/page3.pdf"),
                ],
            )
            result = await tool.execute(params, mock_session, mock_user)

            # Verify result
            assert result.error is None
            assert result.result is not None
            assert len(result.result.documents) == 3
            assert len(result.result.errors) == 0

            # Verify all documents were created
            doc_ids = [doc.id for doc in result.result.documents]
            assert doc_ids == [1, 2, 3]

    async def test_execute_with_errors(self, tool, mock_user):
        """Test tool execution when some URLs fail."""
        mock_session = AsyncMock()

        # Mock response with one success and two errors
        mock_doc = DocumentResponse(
            id=1,
            company_id=1,
            filename="success.txt",
            storage_key="documents/company_1/success.txt",
            checksum="abc123",
            content_type="text/plain",
            file_size=1024,
            extraction_status="pending",
            extracted_content_path=None,
            extraction_started_at=None,
            extraction_completed_at=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_response = BulkUrlUploadResponse(
            documents=[mock_doc],
            errors=[
                "Failed to download https://example.com/bad1",
                "Failed to upload https://example.com/bad2: Invalid content",
            ],
        )

        with patch(
            "packages.agents.tools.tools.add_urls_as_documents.upload_documents_from_urls"
        ) as mock_upload:
            mock_upload.return_value = mock_response

            # Execute tool
            params = AddUrlsAsDocumentsParameters(
                matrix_id=123,
                entity_set_id=10,
                urls=[
                    HttpUrl("https://example.com/good"),
                    HttpUrl("https://example.com/bad1"),
                    HttpUrl("https://example.com/bad2"),
                ],
            )
            result = await tool.execute(params, mock_session, mock_user)

            # Verify result has both successes and errors
            assert result.error is None
            assert result.result is not None
            assert len(result.result.documents) == 1
            assert len(result.result.errors) == 2
            assert "bad1" in result.result.errors[0]
            assert "bad2" in result.result.errors[1]

    async def test_execute_all_urls_fail(self, tool, mock_user):
        """Test tool execution when all URLs fail."""
        mock_session = AsyncMock()

        # Mock response with no documents, only errors
        mock_response = BulkUrlUploadResponse(
            documents=[],
            errors=[
                "Failed to download https://example.com/bad1",
                "Failed to download https://example.com/bad2",
            ],
        )

        with patch(
            "packages.agents.tools.tools.add_urls_as_documents.upload_documents_from_urls"
        ) as mock_upload:
            mock_upload.return_value = mock_response

            # Execute tool
            params = AddUrlsAsDocumentsParameters(
                matrix_id=123,
                entity_set_id=10,
                urls=[
                    HttpUrl("https://example.com/bad1"),
                    HttpUrl("https://example.com/bad2"),
                ],
            )
            result = await tool.execute(params, mock_session, mock_user)

            # Verify result has no documents but has errors
            assert result.error is None
            assert result.result is not None
            assert len(result.result.documents) == 0
            assert len(result.result.errors) == 2

    async def test_execute_route_exception(self, tool, mock_user):
        """Test tool execution when route raises exception."""
        mock_session = AsyncMock()

        # Mock route raising exception
        with patch(
            "packages.agents.tools.tools.add_urls_as_documents.upload_documents_from_urls"
        ) as mock_upload:
            mock_upload.side_effect = Exception("Entity set not found")

            # Execute tool
            params = AddUrlsAsDocumentsParameters(
                matrix_id=123,
                entity_set_id=999,
                urls=[HttpUrl("https://example.com/page1")],
            )
            result = await tool.execute(params, mock_session, mock_user)

            # Verify error result
            assert result.result is None
            assert result.error is not None
            assert "Entity set not found" in result.error.error

    def test_tool_schema_format(self):
        """Test that tool schema is in correct format for OpenAI function calling."""
        definition = AddUrlsAsDocumentsTool.definition()

        # Check overall structure
        assert isinstance(definition.parameters, dict)
        assert "type" in definition.parameters
        assert definition.parameters["type"] == "object"
        assert "properties" in definition.parameters

        # Check matrix_id parameter (required)
        matrix_id_param = definition.parameters["properties"]["matrix_id"]
        assert "type" in matrix_id_param
        assert "description" in matrix_id_param

        # Check entity_set_id parameter (required)
        entity_set_id_param = definition.parameters["properties"]["entity_set_id"]
        assert "type" in entity_set_id_param
        assert "description" in entity_set_id_param

        # Check urls parameter (required, array)
        urls_param = definition.parameters["properties"]["urls"]
        assert "type" in urls_param
        assert "description" in urls_param
