import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from packages.matrices.repositories.matrix_repository import (
    MatrixRepository,
)
from packages.matrices.models.database.matrix import MatrixEntity


class TestMatrixRepository:
    """Unit tests for MatrixRepository."""

    @pytest.fixture
    async def matrix_repo(self, test_db):
        """Create a MatrixRepository instance."""
        return MatrixRepository()

    @pytest.fixture(autouse=True)
    def setup_span_mock(self):
        """Set up the span mock to work properly with async methods."""
        mock_span = MagicMock()
        mock_span.__aenter__ = AsyncMock(return_value=mock_span)
        mock_span.__aexit__ = AsyncMock(return_value=None)
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=None)

        with patch(
            "common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span",
            return_value=mock_span,
        ):
            yield

    @pytest.mark.asyncio
    async def test_get_valid_ids(
        self, matrix_repo, test_db, sample_workspace, sample_company
    ):
        """Test getting valid matrix IDs."""
        # Create matrices
        matrix1 = MatrixEntity(
            name="Matrix 1",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )
        matrix2 = MatrixEntity(
            name="Matrix 2",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )
        matrix3 = MatrixEntity(
            name="Matrix 3",
            deleted=True,
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )  # Deleted
        test_db.add_all([matrix1, matrix2, matrix3])
        await test_db.commit()
        await test_db.refresh(matrix1)
        await test_db.refresh(matrix2)
        await test_db.refresh(matrix3)

        # Test with mix of valid, invalid, and deleted IDs
        test_ids = [matrix1.id, matrix2.id, matrix3.id, 999]
        valid_ids = await matrix_repo.get_valid_ids(test_ids)

        assert len(valid_ids) == 2
        assert matrix1.id in valid_ids
        assert matrix2.id in valid_ids
        assert matrix3.id not in valid_ids  # Excluded because deleted
        assert 999 not in valid_ids  # Excluded because doesn't exist

    @pytest.mark.asyncio
    async def test_get_valid_ids_empty_list(self, matrix_repo):
        """Test get_valid_ids with empty list."""
        result = await matrix_repo.get_valid_ids([])
        assert result == []

    @pytest.mark.asyncio
    async def test_get_valid_ids_nonexistent(self, matrix_repo):
        """Test get_valid_ids with non-existent IDs."""
        result = await matrix_repo.get_valid_ids([999, 998, 997])
        assert result == []

    @pytest.mark.asyncio
    async def test_soft_delete_functionality_inheritance(
        self, matrix_repo, sample_matrix
    ):
        """Test that inherited soft delete methods work correctly."""
        # Test soft_delete method from base repository
        result = await matrix_repo.soft_delete(sample_matrix.id)
        assert result is True

        # Verify matrix is soft deleted
        retrieved = await matrix_repo.get(sample_matrix.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_bulk_soft_delete_functionality_inheritance(
        self, matrix_repo, test_db, sample_workspace, sample_company
    ):
        """Test that inherited bulk_soft_delete method works correctly."""
        # Create multiple matrices
        matrices = []
        for i in range(3):
            matrix = MatrixEntity(
                name=f"Matrix {i}",
                company_id=sample_company.id,
                description=f"Description {i}",
                workspace_id=sample_workspace.id,
            )
            matrices.append(matrix)

        test_db.add_all(matrices)
        await test_db.commit()

        for matrix in matrices:
            await test_db.refresh(matrix)

        # Test bulk_soft_delete method from base repository
        matrix_ids = [matrix.id for matrix in matrices]
        result = await matrix_repo.bulk_soft_delete(matrix_ids)

        assert result == 3

        # Verify all matrices are soft deleted
        for matrix in matrices:
            retrieved = await matrix_repo.get(matrix.id)
            assert retrieved is None
