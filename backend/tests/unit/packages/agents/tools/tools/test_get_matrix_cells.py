import pytest
import hashlib
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from packages.agents.tools.base import ToolPermission
from packages.agents.tools.tools.get_matrix_cells import (
    GetMatrixCellsTool,
    GetMatrixCellsParameters,
)
from packages.matrices.models.domain.matrix_enums import (
    MatrixCellStatus,
    CellType,
    EntityType,
    EntityRole,
)
from packages.matrices.models.schemas.matrix import MatrixCellResponse
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.matrices.models.database.matrix import MatrixCellEntity
from packages.matrices.models.database.matrix_entity_set import (
    MatrixEntitySetEntity,
    MatrixEntitySetMemberEntity,
    MatrixCellEntityReferenceEntity,
)
from packages.documents.models.database.document import DocumentEntity
from packages.questions.models.database.question import QuestionEntity


class TestGetMatrixCellsTool:
    """Test GetMatrixCellsTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return GetMatrixCellsTool()

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return AuthenticatedUser(company_id=1, user_id=1)

    def test_tool_definition(self):
        """Test tool definition is correctly configured."""
        definition = GetMatrixCellsTool.definition()

        assert definition.name == "get_matrix_cells"
        assert (
            definition.description
            == "Get matrix cells, optionally filtered by document or question"
        )
        assert "properties" in definition.parameters
        assert "matrix_id" in definition.parameters["properties"]
        assert "document_id" in definition.parameters["properties"]
        assert "question_id" in definition.parameters["properties"]

    def test_permissions(self):
        """Test tool has correct permissions."""

        permissions = GetMatrixCellsTool.permissions()
        assert permissions == ToolPermission.READ

    def test_parameter_class(self):
        """Test parameter class is correctly configured."""
        param_class = GetMatrixCellsTool.parameter_class()
        assert param_class == GetMatrixCellsParameters

    def test_parameters_validation(self):
        """Test parameter validation."""
        # Valid parameters with all fields
        params = GetMatrixCellsParameters(matrix_id=123, document_id=10, question_id=5)
        assert params.matrix_id == 123
        assert params.document_id == 10
        assert params.question_id == 5

        # Valid parameters with only matrix_id
        params_minimal = GetMatrixCellsParameters(matrix_id=456)
        assert params_minimal.matrix_id == 456
        assert params_minimal.document_id is None
        assert params_minimal.question_id is None

        # Invalid parameters should raise validation error
        with pytest.raises(ValueError):
            GetMatrixCellsParameters()  # Missing required matrix_id

    async def test_execute_all_cells(self, tool, mock_user):
        """Test successful tool execution getting all cells for a matrix."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock matrix cell data - conform to MatrixCellResponse structure
        mock_cells = [
            MatrixCellResponse(
                id=1,
                matrix_id=123,
                entity_refs=[],
                current_answer_set_id=None,
                status=MatrixCellStatus.COMPLETED,
                created_at=datetime(2023, 1, 1),
                updated_at=datetime(2023, 1, 1),
            ),
            MatrixCellResponse(
                id=2,
                matrix_id=123,
                entity_refs=[],
                current_answer_set_id=25,
                status=MatrixCellStatus.PENDING,
                created_at=datetime(2023, 1, 2),
                updated_at=datetime(2023, 1, 2),
            ),
            MatrixCellResponse(
                id=3,
                matrix_id=123,
                entity_refs=[],
                current_answer_set_id=None,
                status=MatrixCellStatus.FAILED,
                created_at=datetime(2023, 1, 3),
                updated_at=datetime(2023, 1, 3),
            ),
        ]

        # Mock the get_matrix_cells function
        with patch(
            "packages.agents.tools.tools.get_matrix_cells.get_matrix_cells"
        ) as mock_get_matrix_cells:
            mock_get_matrix_cells.return_value = mock_cells

            # Execute tool without filters
            params = GetMatrixCellsParameters(matrix_id=123)
            result = await tool.execute(params, mock_session, mock_user)

            # Verify result
            assert result.error is None
            assert result.result is not None
            assert len(result.result.cells) == 3

            # Check first cell
            first_cell = result.result.cells[0]
            assert first_cell.id == 1
            assert first_cell.matrix_id == 123
            assert first_cell.status.value == MatrixCellStatus.COMPLETED.value
            assert first_cell.current_answer_set_id is None

            # Check second cell
            second_cell = result.result.cells[1]
            assert second_cell.id == 2
            assert second_cell.matrix_id == 123
            assert second_cell.current_answer_set_id == 25
            assert second_cell.status.value == MatrixCellStatus.PENDING.value

            # Verify function was called correctly
            mock_get_matrix_cells.assert_called_once_with(
                matrix_id=123, document_id=None, question_id=None, db=mock_session
            )

    async def test_execute_filtered_by_document(self, tool, mock_user):
        """Test successful tool execution filtered by document."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock cells for specific document
        mock_cells = [
            MatrixCellResponse(
                id=1,
                matrix_id=123,
                entity_refs=[],
                current_answer_set_id=15,
                status=MatrixCellStatus.COMPLETED,
                created_at=datetime(2023, 1, 1),
                updated_at=datetime(2023, 1, 1),
            ),
            MatrixCellResponse(
                id=2,
                matrix_id=123,
                entity_refs=[],
                current_answer_set_id=None,
                status=MatrixCellStatus.PROCESSING,
                created_at=datetime(2023, 1, 2),
                updated_at=datetime(2023, 1, 2),
            ),
        ]

        # Mock the get_matrix_cells function
        with patch(
            "packages.agents.tools.tools.get_matrix_cells.get_matrix_cells"
        ) as mock_get_matrix_cells:
            mock_get_matrix_cells.return_value = mock_cells

            # Execute tool with document filter
            params = GetMatrixCellsParameters(matrix_id=123, document_id=10)
            result = await tool.execute(params, mock_session, mock_user)

            # Verify result
            assert result.error is None
            assert result.result is not None
            assert len(result.result.cells) == 2

            # Verify all cells belong to the correct matrix
            assert all(cell.matrix_id == 123 for cell in result.result.cells)

            # Verify function was called correctly
            mock_get_matrix_cells.assert_called_once_with(
                matrix_id=123, document_id=10, question_id=None, db=mock_session
            )

    async def test_execute_filtered_by_question(self, tool, mock_user):
        """Test successful tool execution filtered by question."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock cells for specific question
        mock_cells = [
            MatrixCellResponse(
                id=5,
                matrix_id=123,
                entity_refs=[],
                current_answer_set_id=30,
                status=MatrixCellStatus.COMPLETED,
                created_at=datetime(2023, 1, 1),
                updated_at=datetime(2023, 1, 1),
            ),
            MatrixCellResponse(
                id=6,
                matrix_id=123,
                entity_refs=[],
                current_answer_set_id=None,
                status=MatrixCellStatus.PENDING,
                created_at=datetime(2023, 1, 2),
                updated_at=datetime(2023, 1, 2),
            ),
            MatrixCellResponse(
                id=7,
                matrix_id=123,
                entity_refs=[],
                current_answer_set_id=32,
                status=MatrixCellStatus.FAILED,
                created_at=datetime(2023, 1, 3),
                updated_at=datetime(2023, 1, 3),
            ),
        ]

        # Mock the get_matrix_cells function
        with patch(
            "packages.agents.tools.tools.get_matrix_cells.get_matrix_cells"
        ) as mock_get_matrix_cells:
            mock_get_matrix_cells.return_value = mock_cells

            # Execute tool with question filter
            params = GetMatrixCellsParameters(matrix_id=123, question_id=7)
            result = await tool.execute(params, mock_session, mock_user)

            # Verify result
            assert result.error is None
            assert result.result is not None
            assert len(result.result.cells) == 3

            # Verify all cells belong to the correct matrix
            assert all(cell.matrix_id == 123 for cell in result.result.cells)

            # Verify function was called correctly
            mock_get_matrix_cells.assert_called_once_with(
                matrix_id=123, document_id=None, question_id=7, db=mock_session
            )

    async def test_execute_empty_result(self, tool, mock_user):
        """Test tool execution with no cells found."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock empty result
        with patch(
            "packages.agents.tools.tools.get_matrix_cells.get_matrix_cells"
        ) as mock_get_matrix_cells:
            mock_get_matrix_cells.return_value = []

            # Execute tool
            params = GetMatrixCellsParameters(matrix_id=999)
            result = await tool.execute(params, mock_session, mock_user)

            # Verify result
            assert result.error is None
            assert result.result is not None
            assert len(result.result.cells) == 0

            # Verify function was called correctly
            mock_get_matrix_cells.assert_called_once_with(
                matrix_id=999, document_id=None, question_id=None, db=mock_session
            )

    async def test_execute_service_exception(self, tool, mock_user):
        """Test tool execution when service raises exception."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock function exception
        with patch(
            "packages.agents.tools.tools.get_matrix_cells.get_matrix_cells"
        ) as mock_get_matrix_cells:
            mock_get_matrix_cells.side_effect = Exception("Matrix not found")

            # Execute tool
            params = GetMatrixCellsParameters(matrix_id=123)
            result = await tool.execute(params, mock_session, mock_user)

            # Verify error result
            assert result.result is None
            assert result.error is not None
            assert "Matrix not found" in result.error.error

    async def test_execute_different_cell_statuses(self, tool, mock_user):
        """Test tool execution with cells having different statuses."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock cells with various statuses
        mock_cells = [
            MatrixCellResponse(
                id=1,
                matrix_id=123,
                entity_refs=[],
                current_answer_set_id=None,
                status=MatrixCellStatus.PENDING,
                created_at=datetime(2023, 1, 1),
                updated_at=datetime(2023, 1, 1),
            ),
            MatrixCellResponse(
                id=2,
                matrix_id=123,
                entity_refs=[],
                current_answer_set_id=None,
                status=MatrixCellStatus.PROCESSING,
                created_at=datetime(2023, 1, 2),
                updated_at=datetime(2023, 1, 2),
            ),
            MatrixCellResponse(
                id=3,
                matrix_id=123,
                entity_refs=[],
                current_answer_set_id=25,
                status=MatrixCellStatus.COMPLETED,
                created_at=datetime(2023, 1, 3),
                updated_at=datetime(2023, 1, 3),
            ),
            MatrixCellResponse(
                id=4,
                matrix_id=123,
                entity_refs=[],
                current_answer_set_id=None,
                status=MatrixCellStatus.FAILED,
                created_at=datetime(2023, 1, 4),
                updated_at=datetime(2023, 1, 4),
            ),
        ]

        with patch(
            "packages.agents.tools.tools.get_matrix_cells.get_matrix_cells"
        ) as mock_get_matrix_cells:
            mock_get_matrix_cells.return_value = mock_cells

            # Execute tool
            params = GetMatrixCellsParameters(matrix_id=123)
            result = await tool.execute(params, mock_session, mock_user)

            # Verify result handles all statuses
            assert result.error is None
            assert result.result is not None
            assert len(result.result.cells) == 4

            # Check statuses
            statuses = [cell.status.value for cell in result.result.cells]
            assert MatrixCellStatus.PENDING.value in statuses
            assert MatrixCellStatus.PROCESSING.value in statuses
            assert MatrixCellStatus.COMPLETED.value in statuses
            assert MatrixCellStatus.FAILED.value in statuses

    async def test_execute_document_filter_priority(self, tool, mock_user):
        """Test that document filter takes priority over question filter."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock cells for document filter
        mock_cells = [
            MatrixCellResponse(
                id=1,
                matrix_id=123,
                entity_refs=[],
                current_answer_set_id=15,
                status=MatrixCellStatus.COMPLETED,
                created_at=datetime(2023, 1, 1),
                updated_at=datetime(2023, 1, 1),
            )
        ]

        with patch(
            "packages.agents.tools.tools.get_matrix_cells.get_matrix_cells"
        ) as mock_get_matrix_cells:
            mock_get_matrix_cells.return_value = mock_cells

            # Execute tool with both document and question filters
            params = GetMatrixCellsParameters(
                matrix_id=123, document_id=10, question_id=7
            )
            result = await tool.execute(params, mock_session, mock_user)

            # Verify result
            assert result.error is None
            assert result.result is not None
            assert len(result.result.cells) == 1

            # Verify function was called with both filters
            mock_get_matrix_cells.assert_called_once_with(
                matrix_id=123, document_id=10, question_id=7, db=mock_session
            )

    def test_tool_schema_format(self):
        """Test that tool schema is in correct format for OpenAI function calling."""
        definition = GetMatrixCellsTool.definition()

        # Check overall structure
        assert isinstance(definition.parameters, dict)
        assert "type" in definition.parameters
        assert definition.parameters["type"] == "object"
        assert "properties" in definition.parameters

        # Check matrix_id parameter (required)
        matrix_id_param = definition.parameters["properties"]["matrix_id"]
        assert "type" in matrix_id_param
        assert "description" in matrix_id_param
        assert matrix_id_param["description"] == "the matrix id to get cells for"

        # Check document_id parameter (optional)
        document_id_param = definition.parameters["properties"]["document_id"]
        assert "anyOf" in document_id_param  # Optional[int] generates anyOf
        assert "description" in document_id_param
        assert (
            document_id_param["description"] == "optional document id to filter cells"
        )

        # Check question_id parameter (optional)
        question_id_param = definition.parameters["properties"]["question_id"]
        assert "anyOf" in question_id_param  # Optional[int] generates anyOf
        assert "description" in question_id_param
        assert (
            question_id_param["description"] == "optional question id to filter cells"
        )


class TestGetMatrixCellsToolIntegration:
    """Integration tests that hit real DB without mocking."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return GetMatrixCellsTool()

    @pytest.fixture
    async def entity_sets_with_docs_and_questions(
        self, test_db, sample_matrix, sample_company
    ):
        """Create entity sets with 2 documents and 2 questions."""
        # Create documents
        doc1 = DocumentEntity(
            filename="doc1.pdf",
            storage_key="docs/doc1.pdf",
            checksum="checksum1",
            content_type="application/pdf",
            file_size=1024,
            company_id=sample_company.id,
        )
        doc2 = DocumentEntity(
            filename="doc2.pdf",
            storage_key="docs/doc2.pdf",
            checksum="checksum2",
            content_type="application/pdf",
            file_size=2048,
            company_id=sample_company.id,
        )
        test_db.add_all([doc1, doc2])
        await test_db.commit()
        await test_db.refresh(doc1)
        await test_db.refresh(doc2)

        # Create questions
        question1 = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Question 1",
            question_type_id=1,
            company_id=sample_company.id,
        )
        question2 = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Question 2",
            question_type_id=1,
            company_id=sample_company.id,
        )
        test_db.add_all([question1, question2])
        await test_db.commit()
        await test_db.refresh(question1)
        await test_db.refresh(question2)

        # Get existing entity sets from sample_matrix fixture
        result = await test_db.execute(
            select(MatrixEntitySetEntity).where(
                MatrixEntitySetEntity.matrix_id == sample_matrix.id,
                MatrixEntitySetEntity.entity_type == EntityType.DOCUMENT.value,
            )
        )
        doc_entity_set = result.scalar_one()

        result = await test_db.execute(
            select(MatrixEntitySetEntity).where(
                MatrixEntitySetEntity.matrix_id == sample_matrix.id,
                MatrixEntitySetEntity.entity_type == EntityType.QUESTION.value,
            )
        )
        question_entity_set = result.scalar_one()

        # Create entity set members
        doc_member1 = MatrixEntitySetMemberEntity(
            entity_set_id=doc_entity_set.id,
            entity_type=EntityType.DOCUMENT.value,
            entity_id=doc1.id,
            member_order=0,
            company_id=sample_company.id,
        )
        doc_member2 = MatrixEntitySetMemberEntity(
            entity_set_id=doc_entity_set.id,
            entity_type=EntityType.DOCUMENT.value,
            entity_id=doc2.id,
            member_order=1,
            company_id=sample_company.id,
        )
        q_member1 = MatrixEntitySetMemberEntity(
            entity_set_id=question_entity_set.id,
            entity_type=EntityType.QUESTION.value,
            entity_id=question1.id,
            member_order=0,
            company_id=sample_company.id,
        )
        q_member2 = MatrixEntitySetMemberEntity(
            entity_set_id=question_entity_set.id,
            entity_type=EntityType.QUESTION.value,
            entity_id=question2.id,
            member_order=1,
            company_id=sample_company.id,
        )
        test_db.add_all([doc_member1, doc_member2, q_member1, q_member2])
        await test_db.commit()
        for member in [doc_member1, doc_member2, q_member1, q_member2]:
            await test_db.refresh(member)

        return {
            "doc_entity_set": doc_entity_set,
            "question_entity_set": question_entity_set,
            "doc1": doc1,
            "doc2": doc2,
            "question1": question1,
            "question2": question2,
            "doc_member1": doc_member1,
            "doc_member2": doc_member2,
            "q_member1": q_member1,
            "q_member2": q_member2,
        }

    async def _create_cell_with_refs(
        self,
        test_db,
        sample_matrix,
        sample_company,
        doc_entity_set,
        question_entity_set,
        doc_member,
        q_member,
        status="completed",
    ):
        """Helper to create a cell with entity refs."""
        sig = hashlib.md5(
            f"{sample_matrix.id}_{doc_member.id}_{q_member.id}".encode()
        ).hexdigest()
        cell = MatrixCellEntity(
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            cell_type=CellType.STANDARD.value,
            status=status,
            cell_signature=sig,
        )
        test_db.add(cell)
        await test_db.commit()
        await test_db.refresh(cell)

        # Create entity refs
        test_db.add_all(
            [
                MatrixCellEntityReferenceEntity(
                    matrix_id=sample_matrix.id,
                    matrix_cell_id=cell.id,
                    entity_set_id=doc_entity_set.id,
                    entity_set_member_id=doc_member.id,
                    role=EntityRole.DOCUMENT.value,
                    entity_order=0,
                    company_id=sample_company.id,
                ),
                MatrixCellEntityReferenceEntity(
                    matrix_id=sample_matrix.id,
                    matrix_cell_id=cell.id,
                    entity_set_id=question_entity_set.id,
                    entity_set_member_id=q_member.id,
                    role=EntityRole.QUESTION.value,
                    entity_order=1,
                    company_id=sample_company.id,
                ),
            ]
        )
        await test_db.commit()
        return cell

    async def test_execute_all_cells(
        self,
        tool,
        test_db,
        test_user,
        sample_matrix,
        sample_company,
        entity_sets_with_docs_and_questions,
    ):
        """Test successful tool execution getting all cells for a matrix."""
        entities = entity_sets_with_docs_and_questions

        # Create 3 cells with entity refs
        cell1 = await self._create_cell_with_refs(
            test_db,
            sample_matrix,
            sample_company,
            entities["doc_entity_set"],
            entities["question_entity_set"],
            entities["doc_member1"],
            entities["q_member1"],
            "completed",
        )
        cell2 = await self._create_cell_with_refs(
            test_db,
            sample_matrix,
            sample_company,
            entities["doc_entity_set"],
            entities["question_entity_set"],
            entities["doc_member2"],
            entities["q_member1"],
            "pending",
        )
        cell3 = await self._create_cell_with_refs(
            test_db,
            sample_matrix,
            sample_company,
            entities["doc_entity_set"],
            entities["question_entity_set"],
            entities["doc_member1"],
            entities["q_member2"],
            "failed",
        )

        # Execute tool
        params = GetMatrixCellsParameters(matrix_id=sample_matrix.id)
        result = await tool.execute(params, test_db, test_user)

        # Verify result
        assert result.error is None
        assert result.result is not None
        assert len(result.result.cells) == 3

        for cell in result.result.cells:
            assert isinstance(cell, MatrixCellResponse)
            assert cell.matrix_id == sample_matrix.id

        cell_ids = {cell.id for cell in result.result.cells}
        assert cell_ids == {cell1.id, cell2.id, cell3.id}

    async def test_execute_filtered_by_document(
        self,
        tool,
        test_db,
        test_user,
        sample_matrix,
        sample_company,
        entity_sets_with_docs_and_questions,
    ):
        """Test successful tool execution filtered by document."""
        entities = entity_sets_with_docs_and_questions

        # Create cells for doc1 with both questions
        cell1 = await self._create_cell_with_refs(
            test_db,
            sample_matrix,
            sample_company,
            entities["doc_entity_set"],
            entities["question_entity_set"],
            entities["doc_member1"],
            entities["q_member1"],
            "completed",
        )
        cell2 = await self._create_cell_with_refs(
            test_db,
            sample_matrix,
            sample_company,
            entities["doc_entity_set"],
            entities["question_entity_set"],
            entities["doc_member1"],
            entities["q_member2"],
            "pending",
        )
        # Create cell for doc2 - should not be returned
        await self._create_cell_with_refs(
            test_db,
            sample_matrix,
            sample_company,
            entities["doc_entity_set"],
            entities["question_entity_set"],
            entities["doc_member2"],
            entities["q_member1"],
            "completed",
        )

        # Execute tool with document filter
        params = GetMatrixCellsParameters(
            matrix_id=sample_matrix.id, document_id=entities["doc1"].id
        )
        result = await tool.execute(params, test_db, test_user)

        # Verify result - should only get cells for doc1
        assert result.error is None
        assert result.result is not None
        assert len(result.result.cells) == 2

        cell_ids = {cell.id for cell in result.result.cells}
        assert cell_ids == {cell1.id, cell2.id}

    async def test_execute_filtered_by_question(
        self,
        tool,
        test_db,
        test_user,
        sample_matrix,
        sample_company,
        entity_sets_with_docs_and_questions,
    ):
        """Test successful tool execution filtered by question."""
        entities = entity_sets_with_docs_and_questions

        # Create cells for question1 with both documents
        cell1 = await self._create_cell_with_refs(
            test_db,
            sample_matrix,
            sample_company,
            entities["doc_entity_set"],
            entities["question_entity_set"],
            entities["doc_member1"],
            entities["q_member1"],
            "completed",
        )
        cell2 = await self._create_cell_with_refs(
            test_db,
            sample_matrix,
            sample_company,
            entities["doc_entity_set"],
            entities["question_entity_set"],
            entities["doc_member2"],
            entities["q_member1"],
            "pending",
        )
        # Create cell for question2 - should not be returned
        await self._create_cell_with_refs(
            test_db,
            sample_matrix,
            sample_company,
            entities["doc_entity_set"],
            entities["question_entity_set"],
            entities["doc_member1"],
            entities["q_member2"],
            "completed",
        )

        # Execute tool with question filter
        params = GetMatrixCellsParameters(
            matrix_id=sample_matrix.id, question_id=entities["question1"].id
        )
        result = await tool.execute(params, test_db, test_user)

        # Verify result - should only get cells for question1
        assert result.error is None
        assert result.result is not None
        assert len(result.result.cells) == 2

        cell_ids = {cell.id for cell in result.result.cells}
        assert cell_ids == {cell1.id, cell2.id}

    async def test_execute_filtered_by_both(
        self,
        tool,
        test_db,
        test_user,
        sample_matrix,
        sample_company,
        entity_sets_with_docs_and_questions,
    ):
        """Test successful tool execution filtered by both document and question."""
        entities = entity_sets_with_docs_and_questions

        # Create cell for doc1 + question1 - should be returned
        cell1 = await self._create_cell_with_refs(
            test_db,
            sample_matrix,
            sample_company,
            entities["doc_entity_set"],
            entities["question_entity_set"],
            entities["doc_member1"],
            entities["q_member1"],
            "completed",
        )
        # Create cells for other combinations - should not be returned
        await self._create_cell_with_refs(
            test_db,
            sample_matrix,
            sample_company,
            entities["doc_entity_set"],
            entities["question_entity_set"],
            entities["doc_member1"],
            entities["q_member2"],
            "pending",
        )
        await self._create_cell_with_refs(
            test_db,
            sample_matrix,
            sample_company,
            entities["doc_entity_set"],
            entities["question_entity_set"],
            entities["doc_member2"],
            entities["q_member1"],
            "failed",
        )
        await self._create_cell_with_refs(
            test_db,
            sample_matrix,
            sample_company,
            entities["doc_entity_set"],
            entities["question_entity_set"],
            entities["doc_member2"],
            entities["q_member2"],
            "completed",
        )

        # Execute tool with both filters
        params = GetMatrixCellsParameters(
            matrix_id=sample_matrix.id,
            document_id=entities["doc1"].id,
            question_id=entities["question1"].id,
        )
        result = await tool.execute(params, test_db, test_user)

        # Verify result - should only get the specific cell
        assert result.error is None
        assert result.result is not None
        assert len(result.result.cells) == 1
        assert result.result.cells[0].id == cell1.id

    async def test_execute_empty_matrix(self, tool, test_db, test_user, sample_matrix):
        """Test successful tool execution with empty matrix."""
        params = GetMatrixCellsParameters(matrix_id=sample_matrix.id)
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.cells) == 0

    async def test_execute_nonexistent_matrix(self, tool, test_db, test_user):
        """Test tool execution with nonexistent matrix returns empty result."""
        params = GetMatrixCellsParameters(matrix_id=99999)
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.cells) == 0
