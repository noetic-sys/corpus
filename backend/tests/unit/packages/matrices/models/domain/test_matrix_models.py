import pytest
import hashlib
from datetime import datetime
from pydantic import ValidationError

from packages.matrices.models.domain.matrix import (
    MatrixModel,
    MatrixCellModel,
    MatrixCellStatus,
)
from packages.matrices.models.domain.matrix_enums import MatrixType, CellType


class TestMatrixModel:
    """Unit tests for MatrixModel."""

    def test_matrix_model_creation(self):
        """Test creating a valid MatrixModel."""
        now = datetime.now()
        matrix = MatrixModel(
            id=1,
            company_id=1,
            workspace_id=2,
            name="Test Matrix",
            description="Test description",
            matrix_type=MatrixType.STANDARD,
            created_at=now,
            updated_at=now,
        )

        assert matrix.id == 1
        assert matrix.workspace_id == 2
        assert matrix.name == "Test Matrix"
        assert matrix.description == "Test description"
        assert matrix.matrix_type == MatrixType.STANDARD
        assert matrix.created_at == now
        assert matrix.updated_at == now

    def test_matrix_model_validation(self):
        """Test MatrixModel validation."""
        with pytest.raises(ValidationError):
            MatrixModel()  # Missing required fields


class TestMatrixCellModel:
    """Unit tests for MatrixCellModel."""

    def test_matrix_cell_model_creation(self):
        """Test creating a valid MatrixCellModel."""
        now = datetime.now()
        cell = MatrixCellModel(
            id=1,
            company_id=1,
            matrix_id=1,
            cell_type=CellType.STANDARD,
            current_answer_set_id=1,
            status=MatrixCellStatus.COMPLETED.value,
            created_at=now,
            updated_at=now,
            cell_signature=hashlib.md5(b"test_matrix_cell_model").hexdigest(),
        )

        assert cell.id == 1
        assert cell.matrix_id == 1
        assert cell.cell_type == CellType.STANDARD
        assert cell.status == MatrixCellStatus.COMPLETED
        assert cell.created_at == now
        assert cell.updated_at == now

    def test_matrix_cell_status_enum(self):
        """Test MatrixCellStatus enum values."""
        assert MatrixCellStatus.PENDING.value == "pending"
        assert MatrixCellStatus.PROCESSING.value == "processing"
        assert MatrixCellStatus.COMPLETED.value == "completed"
        assert MatrixCellStatus.FAILED.value == "failed"
