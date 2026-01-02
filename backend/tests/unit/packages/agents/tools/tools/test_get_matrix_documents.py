import pytest
from unittest.mock import AsyncMock, patch

from packages.agents.tools.base import ToolPermission
from packages.agents.tools.tools.get_matrix_documents import (
    GetMatrixDocumentsTool,
    GetMatrixDocumentsParameters,
)
from packages.documents.models.schemas.document import MatrixDocumentResponse
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.documents.models.database.document import (
    DocumentEntity,
)
from packages.matrices.models.database.matrix_entity_set import (
    MatrixEntitySetEntity,
    MatrixEntitySetMemberEntity,
)
from packages.matrices.models.domain.matrix_enums import EntityType


class TestGetMatrixDocumentsTool:
    """Test GetMatrixDocumentsTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return GetMatrixDocumentsTool()

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return AuthenticatedUser(company_id=1, user_id=1)

    def test_tool_definition(self):
        """Test tool definition is correctly configured."""
        definition = GetMatrixDocumentsTool.definition()

        assert definition.name == "get_matrix_documents"
        assert (
            definition.description
            == "Get all documents associated with a specific matrix"
        )
        assert "properties" in definition.parameters
        assert "matrix_id" in definition.parameters["properties"]

    def test_permissions(self):
        """Test tool has correct permissions."""

        permissions = GetMatrixDocumentsTool.permissions()
        assert permissions == ToolPermission.READ

    def test_parameter_class(self):
        """Test parameter class is correctly configured."""
        param_class = GetMatrixDocumentsTool.parameter_class()
        assert param_class == GetMatrixDocumentsParameters

    def test_parameters_validation(self):
        """Test parameter validation."""
        # Valid parameters
        params = GetMatrixDocumentsParameters(matrix_id=123)
        assert params.matrix_id == 123

        # Invalid parameters should raise validation error
        with pytest.raises(ValueError):
            GetMatrixDocumentsParameters()  # Missing required matrix_id

    def test_tool_schema_format(self):
        """Test that tool schema is in correct format for OpenAI function calling."""
        definition = GetMatrixDocumentsTool.definition()

        # Check overall structure
        assert isinstance(definition.parameters, dict)
        assert "type" in definition.parameters
        assert definition.parameters["type"] == "object"
        assert "properties" in definition.parameters

        # Check matrix_id parameter
        matrix_id_param = definition.parameters["properties"]["matrix_id"]
        assert "type" in matrix_id_param
        assert "description" in matrix_id_param
        assert matrix_id_param["description"] == "the matrix id to get documents for"


class TestGetMatrixDocumentsToolIntegration:
    """Integration tests that hit real DB without mocking."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return GetMatrixDocumentsTool()

    @pytest.fixture
    def mock_storage(self):
        """Mock storage to avoid hitting real buckets."""
        storage_mock = AsyncMock()
        storage_mock.upload = AsyncMock(return_value=True)
        storage_mock.download = AsyncMock(return_value=b"mock file content")
        storage_mock.exists = AsyncMock(return_value=True)
        storage_mock.delete = AsyncMock(return_value=True)

        with patch(
            "packages.documents.services.document_service.get_storage",
            return_value=storage_mock,
        ):
            yield storage_mock

    async def test_execute_with_matrix_documents(
        self, tool, test_db, test_user, sample_matrix, sample_company, mock_storage
    ):
        """Test successful tool execution with documents in matrix."""
        # Create documents
        doc1 = DocumentEntity(
            filename="contract.pdf",
            storage_key="docs/contract.pdf",
            checksum="checksum1",
            content_type="application/pdf",
            file_size=1024,
            company_id=sample_company.id,
        )
        doc2 = DocumentEntity(
            filename="amendment.pdf",
            storage_key="docs/amendment.pdf",
            checksum="checksum2",
            content_type="application/pdf",
            file_size=2048,
            company_id=sample_company.id,
        )
        test_db.add_all([doc1, doc2])
        await test_db.commit()
        await test_db.refresh(doc1)
        await test_db.refresh(doc2)

        # Create entity set for documents
        doc_entity_set = MatrixEntitySetEntity(
            matrix_id=sample_matrix.id,
            name="Documents",
            entity_type=EntityType.DOCUMENT.value,
            company_id=sample_company.id,
        )
        test_db.add(doc_entity_set)
        await test_db.commit()
        await test_db.refresh(doc_entity_set)

        # Add documents as entity set members with labels
        member1 = MatrixEntitySetMemberEntity(
            entity_set_id=doc_entity_set.id,
            entity_type=EntityType.DOCUMENT.value,
            entity_id=doc1.id,
            member_order=0,
            company_id=sample_company.id,
            label="Contract Document",
        )
        member2 = MatrixEntitySetMemberEntity(
            entity_set_id=doc_entity_set.id,
            entity_type=EntityType.DOCUMENT.value,
            entity_id=doc2.id,
            member_order=1,
            company_id=sample_company.id,
            label="Amendment 1",
        )
        test_db.add_all([member1, member2])
        await test_db.commit()

        params = GetMatrixDocumentsParameters(matrix_id=sample_matrix.id)
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.documents) == 2

        for matrix_doc in result.result.documents:
            assert isinstance(matrix_doc, MatrixDocumentResponse)
            assert matrix_doc.matrix_id == sample_matrix.id
            assert matrix_doc.company_id == sample_company.id
            assert matrix_doc.document is not None

        labels = {d.label for d in result.result.documents}
        assert labels == {"Contract Document", "Amendment 1"}

    async def test_execute_empty_matrix(
        self, tool, test_db, test_user, sample_matrix, mock_storage
    ):
        """Test successful tool execution with empty matrix."""
        params = GetMatrixDocumentsParameters(matrix_id=sample_matrix.id)
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.documents) == 0

    async def test_execute_nonexistent_matrix(
        self, tool, test_db, test_user, sample_company, mock_storage
    ):
        """Test tool execution with nonexistent matrix returns empty result."""
        params = GetMatrixDocumentsParameters(matrix_id=99999)
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.documents) == 0

    async def test_execute_with_and_without_labels(
        self, tool, test_db, test_user, sample_matrix, sample_company, mock_storage
    ):
        """Test tool execution with documents having labels and without."""
        # Create documents
        doc1 = DocumentEntity(
            filename="labeled.pdf",
            storage_key="docs/labeled.pdf",
            checksum="checksum1",
            content_type="application/pdf",
            file_size=1024,
            company_id=sample_company.id,
        )
        doc2 = DocumentEntity(
            filename="unlabeled.pdf",
            storage_key="docs/unlabeled.pdf",
            checksum="checksum2",
            content_type="application/pdf",
            file_size=2048,
            company_id=sample_company.id,
        )
        test_db.add_all([doc1, doc2])
        await test_db.commit()
        await test_db.refresh(doc1)
        await test_db.refresh(doc2)

        # Create entity set for documents
        doc_entity_set = MatrixEntitySetEntity(
            matrix_id=sample_matrix.id,
            name="Documents",
            entity_type=EntityType.DOCUMENT.value,
            company_id=sample_company.id,
        )
        test_db.add(doc_entity_set)
        await test_db.commit()
        await test_db.refresh(doc_entity_set)

        # Add documents as entity set members - one with label, one without
        member1 = MatrixEntitySetMemberEntity(
            entity_set_id=doc_entity_set.id,
            entity_type=EntityType.DOCUMENT.value,
            entity_id=doc1.id,
            member_order=0,
            company_id=sample_company.id,
            label="Important Document",
        )
        member2 = MatrixEntitySetMemberEntity(
            entity_set_id=doc_entity_set.id,
            entity_type=EntityType.DOCUMENT.value,
            entity_id=doc2.id,
            member_order=1,
            company_id=sample_company.id,
            label=None,
        )
        test_db.add_all([member1, member2])
        await test_db.commit()

        params = GetMatrixDocumentsParameters(matrix_id=sample_matrix.id)
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.documents) == 2

        # Verify one has label, one doesn't
        labels = [d.label for d in result.result.documents]
        assert "Important Document" in labels
        assert None in labels
