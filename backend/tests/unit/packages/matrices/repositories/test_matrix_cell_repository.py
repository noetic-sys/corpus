from unittest.mock import MagicMock, AsyncMock, patch

import pytest
import hashlib

from packages.matrices.models.domain.matrix import (
    MatrixCellStatus,
    MatrixCellCreateModel,
    MatrixCellUpdateModel,
)
from packages.matrices.models.domain.matrix_enums import CellType
from packages.matrices.repositories.matrix_cell_repository import MatrixCellRepository


class TestMatrixCellRepository:
    """Unit tests for MatrixCellRepository streaming methods."""

    @pytest.fixture
    def matrix_cell_repo(self, test_db):
        """Create a MatrixCellRepository instance with real database session."""
        return MatrixCellRepository()

    @pytest.fixture(autouse=True)
    def setup_span_mock(self):
        """Set up the span mock to work properly with async methods."""
        # Create a mock context manager that works with async
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

    @pytest.fixture
    def sample_matrix_cell_data(self):
        """Sample matrix cell data for testing."""
        return {
            "matrix_id": 1,
            "company_id": 1,
            "cell_type": CellType.STANDARD,
            "status": MatrixCellStatus.PENDING.value,
        }

    def create_matrix_cell_model(self, **overrides):
        """Helper method to create MatrixCellCreateModel with defaults."""
        defaults = {
            "matrix_id": 1,
            "company_id": 1,
            "cell_type": CellType.STANDARD,
            "status": MatrixCellStatus.PENDING,
            "cell_signature": "test_signature",  # Default test signature
        }
        defaults.update(overrides)
        return MatrixCellCreateModel(**defaults)

    @pytest.mark.asyncio
    async def test_get_cells_by_matrix_id(
        self, matrix_cell_repo, sample_matrix_cell_data
    ):
        """Test getting all matrix cells for a given matrix."""
        # Create test data
        matrix_id = 1

        # Create multiple cells for the same matrix
        cell1_model = self.create_matrix_cell_model(
            matrix_id=matrix_id,
        )
        cell2_model = self.create_matrix_cell_model(
            matrix_id=matrix_id,
        )
        cell3_model = self.create_matrix_cell_model(
            matrix_id=matrix_id,
        )

        # Create cells in different matrix (should not be returned)
        other_matrix_cell_model = self.create_matrix_cell_model(
            matrix_id=2,
        )

        cell1 = await matrix_cell_repo.create(cell1_model)
        cell2 = await matrix_cell_repo.create(cell2_model)
        cell3 = await matrix_cell_repo.create(cell3_model)
        await matrix_cell_repo.create(other_matrix_cell_model)

        # Call the method
        result = await matrix_cell_repo.get_cells_by_matrix_id(matrix_id)

        # Assertions
        assert len(result) == 3
        matrix_ids = [cell.matrix_id for cell in result]
        assert all(mid == matrix_id for mid in matrix_ids)

        # Verify we got the right cells
        result_ids = sorted([cell.id for cell in result])
        expected_ids = sorted([cell1.id, cell2.id, cell3.id])
        assert result_ids == expected_ids

    @pytest.mark.asyncio
    async def test_get_cells_by_matrix_id_empty_result(self, matrix_cell_repo):
        """Test getting matrix cells for a matrix with no cells."""
        # Call the method with a matrix ID that has no cells
        result = await matrix_cell_repo.get_cells_by_matrix_id(999)

        # Assertions
        assert result == []

    @pytest.mark.asyncio
    async def test_bulk_create_from_models(self, matrix_cell_repo, sample_company):
        """Test bulk creating matrix cells from domain create models."""
        # Create test models
        create_models = [
            MatrixCellCreateModel(
                matrix_id=1,
                company_id=sample_company.id,
                status=MatrixCellStatus.PENDING,
                cell_type=CellType.STANDARD,
                cell_signature=hashlib.md5(b"test_bulk_1").hexdigest(),
            ),
            MatrixCellCreateModel(
                matrix_id=1,
                company_id=sample_company.id,
                cell_type=CellType.STANDARD,
                status=MatrixCellStatus.PENDING,
                cell_signature=hashlib.md5(b"test_bulk_2").hexdigest(),
            ),
            MatrixCellCreateModel(
                matrix_id=1,
                company_id=sample_company.id,
                cell_type=CellType.STANDARD,
                status=MatrixCellStatus.PROCESSING,
                cell_signature=hashlib.md5(b"test_bulk_3").hexdigest(),
            ),
        ]

        # Call bulk create
        result = await matrix_cell_repo.bulk_create_from_models(create_models)

        # Assertions
        assert len(result) == 3
        for i, cell in enumerate(result):
            assert cell.id is not None  # Should have auto-generated ID
            assert cell.matrix_id == create_models[i].matrix_id
            # Both should be enum objects after processing
            expected_status = (
                create_models[i].status
                if isinstance(create_models[i].status, MatrixCellStatus)
                else MatrixCellStatus(create_models[i].status)
            )
            assert cell.status == expected_status
            assert cell.created_at is not None
            assert cell.updated_at is not None

    @pytest.mark.asyncio
    async def test_bulk_create_from_models_empty_list(self, matrix_cell_repo):
        """Test bulk creating with empty list returns empty list."""
        result = await matrix_cell_repo.bulk_create_from_models([])
        assert result == []

    @pytest.mark.asyncio
    async def test_bulk_update_by_id(self, matrix_cell_repo, sample_matrix_cell_data):
        """Test bulk updating matrix cells by ID."""
        # Create test cells first
        cell1 = await matrix_cell_repo.create(
            self.create_matrix_cell_model(
                matrix_id=1,
                document_id=1,
                question_id=1,
            )
        )
        cell2 = await matrix_cell_repo.create(
            self.create_matrix_cell_model(
                matrix_id=1,
                document_id=1,
                question_id=2,
            )
        )
        cell3 = await matrix_cell_repo.create(
            self.create_matrix_cell_model(
                matrix_id=1,
                document_id=2,
                question_id=1,
            )
        )

        # Update data - cells 1 and 2 to PROCESSING, cell 3 to COMPLETED
        updates = [
            MatrixCellUpdateModel(id=cell1.id, status=MatrixCellStatus.PROCESSING),
            MatrixCellUpdateModel(id=cell2.id, status=MatrixCellStatus.PROCESSING),
            MatrixCellUpdateModel(id=cell3.id, status=MatrixCellStatus.COMPLETED),
        ]

        # Call bulk update
        updated_count = await matrix_cell_repo.bulk_update_by_id(updates)

        # Assertions
        assert updated_count == 3

        # Verify updates were applied
        updated_cell1 = await matrix_cell_repo.get(cell1.id)
        updated_cell2 = await matrix_cell_repo.get(cell2.id)
        updated_cell3 = await matrix_cell_repo.get(cell3.id)

        assert updated_cell1.status == MatrixCellStatus.PROCESSING
        assert updated_cell2.status == MatrixCellStatus.PROCESSING
        assert updated_cell3.status == MatrixCellStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_bulk_update_by_id_empty_list(self, matrix_cell_repo):
        """Test bulk updating with empty list returns 0."""
        result = await matrix_cell_repo.bulk_update_by_id([])
        assert result == 0

    @pytest.mark.asyncio
    async def test_bulk_update_by_id_groups_efficiently(
        self, matrix_cell_repo, sample_matrix_cell_data
    ):
        """Test that bulk update groups similar updates to minimize queries."""
        # Create test cells
        cells = []
        for i in range(5):
            cell = await matrix_cell_repo.create(
                self.create_matrix_cell_model(
                    matrix_id=1,
                    document_id=i + 1,
                    question_id=1,
                )
            )
            cells.append(cell)

        # Update first 3 cells to PROCESSING, last 2 to COMPLETED
        updates = [
            MatrixCellUpdateModel(id=cells[0].id, status=MatrixCellStatus.PROCESSING),
            MatrixCellUpdateModel(id=cells[1].id, status=MatrixCellStatus.PROCESSING),
            MatrixCellUpdateModel(id=cells[2].id, status=MatrixCellStatus.PROCESSING),
            MatrixCellUpdateModel(id=cells[3].id, status=MatrixCellStatus.COMPLETED),
            MatrixCellUpdateModel(id=cells[4].id, status=MatrixCellStatus.COMPLETED),
        ]

        # Call bulk update - should efficiently group the updates
        updated_count = await matrix_cell_repo.bulk_update_by_id(updates)
        assert updated_count == 5

        # Verify all updates were applied correctly
        for i in range(5):
            updated_cell = await matrix_cell_repo.get(cells[i].id)
            if i < 3:
                assert updated_cell.status == MatrixCellStatus.PROCESSING
            else:
                assert updated_cell.status == MatrixCellStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_update_current_answer(
        self, matrix_cell_repo, sample_matrix_cell_data
    ):
        """Test updating the current_answer_set_id for a matrix cell."""
        # Create a matrix cell
        cell_model = self.create_matrix_cell_model(
            matrix_id=1,
            document_id=1,
            question_id=1,
        )

        cell = await matrix_cell_repo.create(cell_model)
        assert cell.current_answer_set_id is None

        # Update with a current answer ID
        answer_id = 123
        updated_cell = await matrix_cell_repo.update_current_answer_set(
            cell.id, answer_id
        )

        # Assertions
        assert updated_cell is not None
        assert updated_cell.current_answer_set_id == answer_id
        assert updated_cell.id == cell.id

        # Verify the update persisted
        retrieved_cell = await matrix_cell_repo.get(cell.id)
        assert retrieved_cell.current_answer_set_id == answer_id

    @pytest.mark.asyncio
    async def test_update_current_answer_nonexistent_cell(self, matrix_cell_repo):
        """Test updating current_answer_set_id for a non-existent matrix cell."""
        # Try to update a non-existent cell
        result = await matrix_cell_repo.update_current_answer_set(999, 123)

        # Should return None for non-existent cell
        assert result is None

    @pytest.mark.asyncio
    async def test_get_cells_by_ids(self, matrix_cell_repo, sample_matrix_cell_data):
        """Test getting matrix cells by a list of IDs."""
        # Create test cells
        cell1 = await matrix_cell_repo.create(
            self.create_matrix_cell_model(
                matrix_id=1,
                document_id=1,
                question_id=1,
            )
        )
        _ = await matrix_cell_repo.create(
            self.create_matrix_cell_model(
                matrix_id=1,
                document_id=1,
                question_id=2,
            )
        )
        cell3 = await matrix_cell_repo.create(
            self.create_matrix_cell_model(
                matrix_id=2,
                document_id=1,
                question_id=1,
            )
        )

        # Call with specific IDs
        result = await matrix_cell_repo.get_cells_by_ids([cell1.id, cell3.id])

        # Assertions
        assert len(result) == 2
        result_ids = sorted([cell.id for cell in result])
        expected_ids = sorted([cell1.id, cell3.id])
        assert result_ids == expected_ids

        # Verify correct cells returned
        for cell in result:
            assert cell.id in [cell1.id, cell3.id]

    @pytest.mark.asyncio
    async def test_get_cells_by_ids_empty_list(self, matrix_cell_repo):
        """Test getting cells by empty ID list returns empty list."""
        result = await matrix_cell_repo.get_cells_by_ids([])
        assert result == []

    @pytest.mark.asyncio
    async def test_get_cells_by_ids_nonexistent_ids(self, matrix_cell_repo):
        """Test getting cells by non-existent IDs returns empty list."""
        result = await matrix_cell_repo.get_cells_by_ids([999, 998, 997])
        assert result == []

    @pytest.mark.asyncio
    async def test_bulk_update_cells_to_pending(
        self, matrix_cell_repo, sample_matrix_cell_data
    ):
        """Test bulk updating matrix cells to pending status."""
        # Create test cells with different statuses
        cell1 = await matrix_cell_repo.create(
            self.create_matrix_cell_model(
                matrix_id=1,
                document_id=1,
                question_id=1,
                status=MatrixCellStatus.COMPLETED,
            )
        )
        cell2 = await matrix_cell_repo.create(
            self.create_matrix_cell_model(
                matrix_id=1,
                document_id=1,
                question_id=2,
                status=MatrixCellStatus.PROCESSING,
            )
        )
        cell3 = await matrix_cell_repo.create(
            self.create_matrix_cell_model(
                matrix_id=1,
                document_id=2,
                question_id=1,
                status=MatrixCellStatus.FAILED,
            )
        )

        # Update cells to have current_answer_set_id
        await matrix_cell_repo.update_current_answer_set(cell1.id, 100)
        await matrix_cell_repo.update_current_answer_set(cell2.id, 200)

        # Call bulk update to pending
        cell_ids = [cell1.id, cell2.id, cell3.id]
        updated_count = await matrix_cell_repo.bulk_update_cells_to_pending(cell_ids)

        # Assertions
        assert updated_count == 3

        # Verify all cells are now pending and current_answer_set_id is cleared
        updated_cell1 = await matrix_cell_repo.get(cell1.id)
        updated_cell2 = await matrix_cell_repo.get(cell2.id)
        updated_cell3 = await matrix_cell_repo.get(cell3.id)

        assert updated_cell1.status == MatrixCellStatus.PENDING
        assert updated_cell1.current_answer_set_id is None
        assert updated_cell2.status == MatrixCellStatus.PENDING
        assert updated_cell2.current_answer_set_id is None
        assert updated_cell3.status == MatrixCellStatus.PENDING
        assert updated_cell3.current_answer_set_id is None

    @pytest.mark.asyncio
    async def test_bulk_update_cells_to_pending_empty_list(self, matrix_cell_repo):
        """Test bulk updating with empty cell ID list returns 0."""
        result = await matrix_cell_repo.bulk_update_cells_to_pending([])
        assert result == 0

    @pytest.mark.asyncio
    async def test_bulk_update_cells_to_pending_nonexistent_ids(self, matrix_cell_repo):
        """Test bulk updating with non-existent cell IDs returns 0."""
        result = await matrix_cell_repo.bulk_update_cells_to_pending([999, 998, 997])
        assert result == 0

    # Soft delete related tests for MatrixCellRepository
    @pytest.mark.asyncio
    async def test_get_cells_by_matrix_id_excludes_deleted(
        self, matrix_cell_repo, sample_matrix_cell_data
    ):
        """Test that get_cells_by_matrix_id excludes soft deleted cells."""
        matrix_id = 1

        # Create cells, one deleted
        cell1 = await matrix_cell_repo.create(
            self.create_matrix_cell_model(
                matrix_id=matrix_id,
                document_id=1,
                question_id=1,
            )
        )
        cell2_model = self.create_matrix_cell_model(
            matrix_id=matrix_id,
            document_id=1,
            question_id=2,
        )
        cell2 = await matrix_cell_repo.create(cell2_model)

        # Soft delete cell2
        await matrix_cell_repo.soft_delete(cell2.id)

        # Get cells by matrix ID
        result = await matrix_cell_repo.get_cells_by_matrix_id(matrix_id)

        assert len(result) == 1
        assert result[0].id == cell1.id

    @pytest.mark.asyncio
    async def test_bulk_soft_delete_by_matrix_ids(
        self, matrix_cell_repo, sample_matrix_cell_data
    ):
        """Test bulk soft deleting matrix cells by matrix IDs."""
        # Create cells in different matrices
        _ = [
            await matrix_cell_repo.create(
                self.create_matrix_cell_model(
                    matrix_id=1,
                    document_id=1,
                    question_id=1,
                )
            ),
            await matrix_cell_repo.create(
                self.create_matrix_cell_model(
                    matrix_id=1,
                    document_id=1,
                    question_id=2,
                )
            ),
        ]
        _ = [
            await matrix_cell_repo.create(
                self.create_matrix_cell_model(
                    matrix_id=2,
                    document_id=1,
                    question_id=1,
                )
            )
        ]
        _ = [
            await matrix_cell_repo.create(
                self.create_matrix_cell_model(
                    matrix_id=3,
                    document_id=1,
                    question_id=1,
                )
            )
        ]

        # Soft delete cells in matrix 1 and 2
        deleted_count = await matrix_cell_repo.bulk_soft_delete_by_matrix_ids([1, 2])

        assert deleted_count == 3  # 2 from matrix1 + 1 from matrix2

        # Verify cells are soft deleted
        m1_cells = await matrix_cell_repo.get_cells_by_matrix_id(1)
        m2_cells = await matrix_cell_repo.get_cells_by_matrix_id(2)
        m3_cells = await matrix_cell_repo.get_cells_by_matrix_id(3)

        assert len(m1_cells) == 0  # Soft deleted
        assert len(m2_cells) == 0  # Soft deleted
        assert len(m3_cells) == 1  # Not deleted

    @pytest.mark.asyncio
    async def test_bulk_soft_delete_empty_lists(self, matrix_cell_repo):
        """Test bulk soft delete with empty lists."""
        assert await matrix_cell_repo.bulk_soft_delete_by_matrix_ids([]) == 0
