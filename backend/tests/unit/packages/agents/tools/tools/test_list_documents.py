import pytest
from unittest.mock import patch

from packages.agents.tools.base import ToolPermission
from packages.agents.tools.tools.list_documents import (
    ListDocumentsTool,
    ListDocumentsParameters,
)
from packages.documents.models.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
)
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.documents.models.database.document import DocumentEntity


class TestListDocumentsTool:
    """Test ListDocumentsTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return ListDocumentsTool()

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return AuthenticatedUser(company_id=1, user_id=1)

    def test_tool_definition(self):
        """Test tool definition is correctly configured."""
        definition = ListDocumentsTool.definition()

        assert definition.name == "list_documents"
        assert definition.description == "List or search documents in the system"
        assert "properties" in definition.parameters
        assert "query" in definition.parameters["properties"]
        assert "content_type" in definition.parameters["properties"]
        assert "limit" in definition.parameters["properties"]
        assert "skip" in definition.parameters["properties"]

    def test_permissions(self):
        """Test tool has correct permissions."""

        permissions = ListDocumentsTool.permissions()
        assert permissions == ToolPermission.READ

    def test_parameter_class(self):
        """Test parameter class is correctly configured."""
        param_class = ListDocumentsTool.parameter_class()
        assert param_class == ListDocumentsParameters

    def test_parameters_validation(self):
        """Test parameter validation."""
        # Valid parameters with all fields
        params = ListDocumentsParameters(
            query="test search", content_type="application/pdf", limit=25, skip=10
        )
        assert params.query == "test search"
        assert params.content_type == "application/pdf"
        assert params.limit == 25
        assert params.skip == 10

        # Valid parameters with defaults
        params_default = ListDocumentsParameters()
        assert params_default.query is None
        assert params_default.content_type is None
        assert params_default.limit == 50
        assert params_default.skip == 0

    def test_tool_schema_format(self):
        """Test that tool schema is in correct format for OpenAI function calling."""
        definition = ListDocumentsTool.definition()

        # Check overall structure
        assert isinstance(definition.parameters, dict)
        assert "type" in definition.parameters
        assert definition.parameters["type"] == "object"
        assert "properties" in definition.parameters

        # Check query parameter (optional)
        query_param = definition.parameters["properties"]["query"]
        assert "anyOf" in query_param  # Optional[str] generates anyOf
        assert "description" in query_param
        assert query_param["description"] == "optional search query to filter documents"

        # Check content_type parameter (optional)
        content_type_param = definition.parameters["properties"]["content_type"]
        assert "anyOf" in content_type_param  # Optional[str] generates anyOf
        assert "description" in content_type_param
        assert content_type_param["description"] == "optional content type filter"

        # Check limit parameter
        limit_param = definition.parameters["properties"]["limit"]
        assert "type" in limit_param
        assert "description" in limit_param
        assert limit_param["default"] == 50

        # Check skip parameter
        skip_param = definition.parameters["properties"]["skip"]
        assert "type" in skip_param
        assert "description" in skip_param
        assert skip_param["default"] == 0


class TestListDocumentsToolIntegration:
    """Integration tests - mocking search provider due to Elasticsearch dependency."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return ListDocumentsTool()

    async def test_execute_list_all_documents(
        self, tool, test_db, test_user, sample_company
    ):
        """Test successful tool execution listing all documents."""
        # Create test documents in DB
        doc1 = DocumentEntity(
            filename="contract.pdf",
            storage_key="docs/contract.pdf",
            checksum="checksum1",
            content_type="application/pdf",
            file_size=1024,
            company_id=sample_company.id,
        )
        doc2 = DocumentEntity(
            filename="agreement.docx",
            storage_key="docs/agreement.docx",
            checksum="checksum2",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size=2048,
            company_id=sample_company.id,
        )
        test_db.add_all([doc1, doc2])
        await test_db.commit()
        await test_db.refresh(doc1)
        await test_db.refresh(doc2)

        # Mock the route response
        mock_response = DocumentListResponse(
            documents=[
                DocumentResponse.model_validate(doc1),
                DocumentResponse.model_validate(doc2),
            ],
            total_count=2,
            skip=0,
            limit=50,
            has_more=False,
        )

        with patch(
            "packages.agents.tools.tools.list_documents.list_documents",
            return_value=mock_response,
        ):
            params = ListDocumentsParameters()
            result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert isinstance(result.result.documents_response, DocumentListResponse)
        assert len(result.result.documents_response.documents) == 2
        assert result.result.documents_response.total_count == 2

        for doc in result.result.documents_response.documents:
            assert isinstance(doc, DocumentResponse)
            assert doc.company_id == sample_company.id

        filenames = {d.filename for d in result.result.documents_response.documents}
        assert filenames == {"contract.pdf", "agreement.docx"}

    async def test_execute_search_with_query(
        self, tool, test_db, test_user, sample_company
    ):
        """Test successful tool execution with search query."""
        doc1 = DocumentEntity(
            filename="contract_2024.pdf",
            storage_key="docs/contract_2024.pdf",
            checksum="checksum1",
            content_type="application/pdf",
            file_size=1024,
            company_id=sample_company.id,
        )
        test_db.add(doc1)
        await test_db.commit()
        await test_db.refresh(doc1)

        mock_response = DocumentListResponse(
            documents=[DocumentResponse.model_validate(doc1)],
            total_count=1,
            skip=0,
            limit=50,
            has_more=False,
        )

        with patch(
            "packages.agents.tools.tools.list_documents.search_documents",
            return_value=mock_response,
        ):
            params = ListDocumentsParameters(query="contract")
            result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert isinstance(result.result.documents_response, DocumentListResponse)
        assert len(result.result.documents_response.documents) == 1
        assert (
            result.result.documents_response.documents[0].filename
            == "contract_2024.pdf"
        )

    async def test_execute_with_content_type_filter(
        self, tool, test_db, test_user, sample_company
    ):
        """Test tool execution with content type filter."""
        pdf_doc = DocumentEntity(
            filename="document.pdf",
            storage_key="docs/document.pdf",
            checksum="checksum1",
            content_type="application/pdf",
            file_size=1024,
            company_id=sample_company.id,
        )
        test_db.add(pdf_doc)
        await test_db.commit()
        await test_db.refresh(pdf_doc)

        mock_response = DocumentListResponse(
            documents=[DocumentResponse.model_validate(pdf_doc)],
            total_count=1,
            skip=0,
            limit=50,
            has_more=False,
        )

        with patch(
            "packages.agents.tools.tools.list_documents.list_documents",
            return_value=mock_response,
        ):
            params = ListDocumentsParameters(content_type="application/pdf")
            result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.documents_response.documents) == 1
        assert (
            result.result.documents_response.documents[0].content_type
            == "application/pdf"
        )

    async def test_execute_pagination(self, tool, test_db, test_user, sample_company):
        """Test tool execution with pagination parameters."""
        documents = []
        for i in range(1, 3):
            doc = DocumentEntity(
                filename=f"doc_{i}.pdf",
                storage_key=f"docs/doc_{i}.pdf",
                checksum=f"checksum{i}",
                content_type="application/pdf",
                file_size=1024,
                company_id=sample_company.id,
            )
            documents.append(doc)

        test_db.add_all(documents)
        await test_db.commit()
        for doc in documents:
            await test_db.refresh(doc)

        mock_response = DocumentListResponse(
            documents=[DocumentResponse.model_validate(d) for d in documents],
            total_count=2,
            skip=0,
            limit=2,
            has_more=False,
        )

        with patch(
            "packages.agents.tools.tools.list_documents.list_documents",
            return_value=mock_response,
        ):
            params = ListDocumentsParameters(limit=2, skip=0)
            result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.documents_response.documents) == 2

    async def test_execute_empty_result(self, tool, test_db, test_user, sample_company):
        """Test tool execution with no documents found."""
        mock_response = DocumentListResponse(
            documents=[], total_count=0, skip=0, limit=50, has_more=False
        )

        with patch(
            "packages.agents.tools.tools.list_documents.list_documents",
            return_value=mock_response,
        ):
            params = ListDocumentsParameters()
            result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert isinstance(result.result.documents_response, DocumentListResponse)
        assert len(result.result.documents_response.documents) == 0
        assert result.result.documents_response.total_count == 0
