import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from packages.agents.tools.base import ToolPermission
from packages.agents.tools.tools.get_matrix_entity_sets import (
    GetMatrixEntitySetsTool,
    GetMatrixEntitySetsParameters,
)
from packages.matrices.models.schemas.matrix_entity_set import (
    MatrixEntitySetsResponse,
    EntitySetResponse,
    EntitySetMemberResponse,
)
from packages.matrices.models.domain.matrix_enums import EntityType, MatrixType
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from datetime import datetime


class TestGetMatrixEntitySetsTool:
    """Test GetMatrixEntitySetsTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return GetMatrixEntitySetsTool()

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return AuthenticatedUser(company_id=1, user_id=1)

    def test_tool_definition(self):
        """Test tool definition is correctly configured."""
        definition = GetMatrixEntitySetsTool.definition()

        assert definition.name == "get_matrix_entity_sets"
        assert "entity sets" in definition.description.lower()
        assert "properties" in definition.parameters
        assert "matrix_id" in definition.parameters["properties"]

    def test_permissions(self):
        """Test tool has correct permissions."""
        permissions = GetMatrixEntitySetsTool.permissions()
        assert permissions == ToolPermission.READ

    def test_parameter_class(self):
        """Test parameter class is correctly configured."""
        param_class = GetMatrixEntitySetsTool.parameter_class()
        assert param_class == GetMatrixEntitySetsParameters

    def test_parameters_validation(self):
        """Test parameter validation."""
        # Valid parameters
        params = GetMatrixEntitySetsParameters(matrix_id=123)
        assert params.matrix_id == 123

        # Invalid parameters should raise validation error
        with pytest.raises(ValueError):
            GetMatrixEntitySetsParameters()  # Missing required fields

    async def test_execute_success(self, tool, mock_user):
        """Test successful tool execution."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock entity sets response
        mock_entity_sets = MatrixEntitySetsResponse(
            matrix_id=123,
            matrix_type=MatrixType.STANDARD,
            entity_sets=[
                EntitySetResponse(
                    id=1,
                    matrix_id=123,
                    name="Documents",
                    entity_type=EntityType.DOCUMENT,
                    created_at=datetime.now(),
                    members=[
                        EntitySetMemberResponse(
                            id=1,
                            entity_set_id=1,
                            entity_type=EntityType.DOCUMENT,
                            entity_id=10,
                            member_order=0,
                            label=None,
                            created_at=datetime.now(),
                        )
                    ],
                ),
                EntitySetResponse(
                    id=2,
                    matrix_id=123,
                    name="Questions",
                    entity_type=EntityType.QUESTION,
                    created_at=datetime.now(),
                    members=[
                        EntitySetMemberResponse(
                            id=2,
                            entity_set_id=2,
                            entity_type=EntityType.QUESTION,
                            entity_id=20,
                            member_order=0,
                            label=None,
                            created_at=datetime.now(),
                        )
                    ],
                ),
            ],
        )

        # Mock the route function
        with patch(
            "packages.agents.tools.tools.get_matrix_entity_sets.get_matrix_entity_sets"
        ) as mock_route:
            mock_route.return_value = mock_entity_sets

            # Execute tool
            params = GetMatrixEntitySetsParameters(matrix_id=123)
            result = await tool.execute(params, mock_session, mock_user)

            # Verify result
            assert result.error is None
            assert result.result is not None
            assert result.result.entity_sets is not None
            assert result.result.entity_sets.matrix_id == 123
            assert len(result.result.entity_sets.entity_sets) == 2
            assert result.result.entity_sets.entity_sets[0].name == "Documents"
            assert result.result.entity_sets.entity_sets[1].name == "Questions"

            # Verify function was called correctly
            mock_route.assert_called_once_with(matrix_id=123, current_user=mock_user)

    async def test_execute_service_exception(self, tool, mock_user):
        """Test tool execution when service raises exception."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock function exception
        with patch(
            "packages.agents.tools.tools.get_matrix_entity_sets.get_matrix_entity_sets"
        ) as mock_route:
            mock_route.side_effect = Exception("Matrix not found")

            # Execute tool
            params = GetMatrixEntitySetsParameters(matrix_id=123)
            result = await tool.execute(params, mock_session, mock_user)

            # Verify error result
            assert result.result is None
            assert result.error is not None
            assert "Matrix not found" in result.error.error
