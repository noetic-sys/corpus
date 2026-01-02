from __future__ import annotations
import enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator

from packages.matrices.models.domain.matrix_enums import MatrixType, CellType
from packages.matrices.models.domain.matrix_entity_set import EntityReference


class MatrixCellStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MatrixModel(BaseModel):
    id: int
    workspace_id: int
    name: str
    description: Optional[str] = None
    company_id: int
    matrix_type: MatrixType
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MatrixCreateModel(BaseModel):
    """Model for creating a new matrix."""

    name: str
    description: Optional[str] = None
    workspace_id: int
    company_id: int
    matrix_type: MatrixType = MatrixType.STANDARD


class MatrixUpdateModel(BaseModel):
    """Model for updating a matrix."""

    name: Optional[str] = None
    description: Optional[str] = None


class MatrixCellCreateModel(BaseModel):
    """Model for creating a new matrix cell (without auto-generated fields).

    NOTE: document_id and question_id removed - cells now use entity_refs for N-dimensional coordinates.
    """

    matrix_id: int
    company_id: int
    status: str
    cell_type: (
        CellType  # REQUIRED - QA worker needs this to determine processing strategy
    )
    cell_signature: str  # Hash of sorted entity refs - computed by application
    current_answer_set_id: Optional[int] = None
    entity_refs: Optional[List[EntityReference]] = (
        None  # Entity references for N-dimensional coordinates
    )

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if isinstance(v, str):
            return v
        elif isinstance(v, MatrixCellStatus):
            return v.value
        return v


class MatrixCellUpdateModel(BaseModel):
    """Model for updating a matrix cell."""

    id: Optional[int] = None  # For bulk updates
    current_answer_set_id: Optional[int] = None
    status: Optional[str] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return v
        elif isinstance(v, MatrixCellStatus):
            return v.value
        return v


class MatrixCellStatsModel(BaseModel):
    """Model for matrix cell statistics by status."""

    total_cells: int
    completed: int
    processing: int
    pending: int
    failed: int
    # Document extraction stats (separate from QA cell stats)
    documents_pending_extraction: int = 0
    documents_failed_extraction: int = 0


class MatrixCellModel(BaseModel):
    """Domain model for matrix cells.

    NOTE: document_id and question_id removed - cells now use entity_refs for N-dimensional coordinates.
    Use MatrixCellEntityReferenceEntity to get the cell's coordinates.
    """

    id: int
    matrix_id: int
    current_answer_set_id: Optional[int] = None
    company_id: int
    status: MatrixCellStatus
    cell_type: (
        CellType  # REQUIRED - QA worker needs this to determine processing strategy
    )
    cell_signature: str  # Hash of sorted entity refs
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if isinstance(v, str):
            # Convert string to enum for domain model
            for status in MatrixCellStatus:
                if status.value == v:
                    return status
            return v
        return v
