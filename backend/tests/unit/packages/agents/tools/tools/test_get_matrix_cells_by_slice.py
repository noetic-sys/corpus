import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from packages.agents.tools.base import ToolPermission
from packages.agents.tools.tools.get_matrix_cells_by_slice import (
    GetMatrixCellsBySliceTool,
    GetMatrixCellsBySliceParameters,
    EntitySetFilterInput,
)
from packages.matrices.models.schemas.matrix import MatrixCellWithAnswerResponse
from packages.matrices.models.schemas.matrix_cell_answer import (
    MatrixCellAnswerResponse,
    AnswerWithCitations,
    TextAnswerDataResponse,
)
from packages.matrices.models.domain.matrix import MatrixCellStatus
from packages.matrices.models.domain.matrix_enums import CellType
from packages.auth.models.domain.authenticated_user import AuthenticatedUser


class TestGetMatrixCellsBySliceTool:
    """Test GetMatrixCellsBySliceTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return GetMatrixCellsBySliceTool()

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return AuthenticatedUser(company_id=1, user_id=1)

    def test_tool_definition(self):
        """Test tool definition is correctly configured."""
        definition = GetMatrixCellsBySliceTool.definition()

        assert definition.name == "get_matrix_cells_by_slice"
        assert "slicing" in definition.description.lower()
        assert "properties" in definition.parameters
        assert "matrix_id" in definition.parameters["properties"]
        assert "entity_set_filters" in definition.parameters["properties"]

    def test_permissions(self):
        """Test tool has correct permissions."""
        permissions = GetMatrixCellsBySliceTool.permissions()
        assert permissions == ToolPermission.READ

    def test_parameter_class(self):
        """Test parameter class is correctly configured."""
        param_class = GetMatrixCellsBySliceTool.parameter_class()
        assert param_class == GetMatrixCellsBySliceParameters

    def test_parameters_validation(self):
        """Test parameter validation."""
        # Valid parameters
        params = GetMatrixCellsBySliceParameters(
            matrix_id=123,
            entity_set_filters=[
                EntitySetFilterInput(
                    entity_set_id=1, entity_ids=[10, 11], role="document"
                )
            ],
        )
        assert params.matrix_id == 123
        assert len(params.entity_set_filters) == 1

        # Invalid parameters should raise validation error
        with pytest.raises(ValueError):
            GetMatrixCellsBySliceParameters()  # Missing required fields

    async def test_execute_success(self, tool, mock_user):
        """Test successful tool execution."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock matrix cells response
        mock_answer = MatrixCellAnswerResponse(
            id=100,
            matrix_cell_id=1,
            question_type_id=1,
            answers=[
                AnswerWithCitations(
                    answer_data=TextAnswerDataResponse(
                        type="text", value="Sample answer"
                    ),
                    citations=[],
                )
            ],
            answer_found=True,
            processing_metadata=None,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00",
        )

        mock_cells = [
            MatrixCellWithAnswerResponse(
                id=1,
                matrix_id=123,
                current_answer_set_id=100,
                status=MatrixCellStatus.COMPLETED,
                cell_type=CellType.STANDARD,
                created_at="2023-01-01T00:00:00",
                updated_at="2023-01-01T00:00:00",
                current_answer=mock_answer,
                entity_refs=[],
            )
        ]

        # Mock the route function
        with patch(
            "packages.agents.tools.tools.get_matrix_cells_by_slice.get_matrix_cells_batch"
        ) as mock_route:
            mock_route.return_value = mock_cells

            # Execute tool
            params = GetMatrixCellsBySliceParameters(
                matrix_id=123,
                entity_set_filters=[
                    EntitySetFilterInput(
                        entity_set_id=1, entity_ids=[10, 11], role="document"
                    ),
                    EntitySetFilterInput(
                        entity_set_id=2, entity_ids=[20], role="question"
                    ),
                ],
            )
            result = await tool.execute(params, mock_session, mock_user)

            # Verify result
            assert result.error is None
            assert result.result is not None
            assert len(result.result.matrix_cells) == 1
            assert result.result.matrix_cells[0].id == 1
            assert result.result.matrix_cells[0].current_answer is not None

            # Verify function was called correctly
            mock_route.assert_called_once()

    async def test_execute_empty_result(self, tool, mock_user):
        """Test tool execution with no cells found."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock empty result
        with patch(
            "packages.agents.tools.tools.get_matrix_cells_by_slice.get_matrix_cells_batch"
        ) as mock_route:
            mock_route.return_value = []

            # Execute tool
            params = GetMatrixCellsBySliceParameters(
                matrix_id=123,
                entity_set_filters=[
                    EntitySetFilterInput(
                        entity_set_id=1, entity_ids=[99], role="document"
                    )
                ],
            )
            result = await tool.execute(params, mock_session, mock_user)

            # Verify result
            assert result.error is None
            assert result.result is not None
            assert len(result.result.matrix_cells) == 0

    async def test_execute_service_exception(self, tool, mock_user):
        """Test tool execution when service raises exception."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock function exception
        with patch(
            "packages.agents.tools.tools.get_matrix_cells_by_slice.get_matrix_cells_batch"
        ) as mock_route:
            mock_route.side_effect = Exception("Invalid entity set filter")

            # Execute tool
            params = GetMatrixCellsBySliceParameters(
                matrix_id=123,
                entity_set_filters=[
                    EntitySetFilterInput(
                        entity_set_id=1, entity_ids=[10], role="document"
                    )
                ],
            )
            result = await tool.execute(params, mock_session, mock_user)

            # Verify error result
            assert result.result is None
            assert result.error is not None
            assert "Invalid entity set filter" in result.error.error
