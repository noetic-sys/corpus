from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
from pydantic import BaseModel, field_validator, ConfigDict
from pydantic.alias_generators import to_camel

from packages.matrices.models.domain.matrix import MatrixCellStatus
from packages.matrices.models.schemas.matrix_cell_answer import MatrixCellAnswerResponse
from packages.matrices.models.domain.matrix_enums import (
    EntityRole,
    EntityType,
    MatrixType,
)


class EntitySetSummary(BaseModel):
    """Summary of an entity set for structure metadata."""

    id: int
    name: str
    entity_type: EntityType
    member_count: int
    description: Optional[str] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class MatrixStructureResponse(BaseModel):
    """Matrix structure metadata for document generation agents.

    Provides information about how the matrix is organized and how to
    interpret cell data when fetching from the API.
    """

    matrix_id: int
    matrix_name: str
    matrix_type: MatrixType
    entity_sets: List[EntitySetSummary]
    explanation: str
    roles_explanation: Dict[str, str]
    system_placeholders: Dict[str, str]
    cell_structure: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class MatrixDuplicationType(str, Enum):
    """Types of matrix duplication."""

    DOCUMENTS_ONLY = "DOCUMENTS_ONLY"
    QUESTIONS_ONLY = "QUESTIONS_ONLY"
    FULL_MATRIX = "FULL_MATRIX"


# Matrix schemas
class MatrixBase(BaseModel):
    name: str
    description: Optional[str] = None
    workspace_id: int

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class MatrixCreate(MatrixBase):
    matrix_type: MatrixType = MatrixType.STANDARD


class MatrixUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class MatrixListResponse(MatrixBase):
    id: int
    workspace_id: int
    name: str
    description: Optional[str] = None
    company_id: int
    matrix_type: MatrixType
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )


class MatrixResponse(MatrixBase):
    id: int
    matrix_type: MatrixType
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )


# Matrix Cell schemas
class MatrixCellBase(BaseModel):
    current_answer_set_id: Optional[int] = None
    status: MatrixCellStatus = MatrixCellStatus.PENDING

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class MatrixCellUpdate(BaseModel):
    current_answer_set_id: Optional[int] = None
    status: Optional[MatrixCellStatus] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        use_enum_values=True,
    )

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            # Convert string to enum
            for status in MatrixCellStatus:
                if status.value == v:
                    return status
            raise ValueError(f"Invalid status value: {v}")
        return v


class EntityRefResponse(BaseModel):
    """Entity reference response - represents one dimension of a cell's N-dimensional coordinate."""

    id: int
    entity_set_id: int
    entity_set_member_id: int
    entity_type: EntityType
    entity_id: int
    role: EntityRole
    entity_order: int

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class MatrixCellResponse(MatrixCellBase):
    id: int
    matrix_id: int
    entity_refs: List[EntityRefResponse]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )


class MatrixCellWithAnswerResponse(BaseModel):
    """Matrix cell response that includes the current answer data."""

    id: int
    matrix_id: int
    entity_refs: List[EntityRefResponse]
    current_answer_set_id: Optional[int] = None
    status: MatrixCellStatus
    created_at: datetime
    updated_at: datetime
    current_answer: Optional[MatrixCellAnswerResponse] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )


class MatrixWithGridResponse(MatrixBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )


class EntitySetFilter(BaseModel):
    """Filter for entities in an entity set.

    Role is REQUIRED - it identifies which axis/dimension this filter applies to.
    For correlation matrices, the same entity_set_id appears multiple times
    with different roles (e.g., LEFT and RIGHT both using the documents entity set).
    """

    entity_set_id: int
    entity_ids: List[int]
    role: EntityRole  # REQUIRED - identifies the axis

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class MatrixReprocessRequest(BaseModel):
    """Request schema for matrix reprocessing operations.

    Uses entity_set_filters to specify entities across any dimension.
    Frontend maps entity sets to documents/questions.
    """

    entity_set_filters: Optional[List[EntitySetFilter]] = None
    cell_ids: Optional[List[int]] = None
    whole_matrix: bool = False

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class MatrixCellReprocessResponse(BaseModel):
    """Response schema for matrix cell reprocessing operations."""

    cells_reprocessed: int
    message: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class MatrixSoftDeleteRequest(BaseModel):
    """Request schema for soft delete operations on matrix entities.

    Uses entity_set_filters to specify entities across any dimension.
    Frontend maps entity sets to documents/questions.
    """

    entity_set_filters: Optional[List[EntitySetFilter]] = None
    matrix_ids: Optional[List[int]] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class MatrixSoftDeleteResponse(BaseModel):
    """Response schema for soft delete operations."""

    entities_deleted: int
    cells_deleted: int
    message: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class TemplateVariableOverride(BaseModel):
    """Template variable value override for matrix duplication."""

    template_variable_id: int
    new_value: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class MatrixDuplicateRequest(BaseModel):
    """Request schema for matrix duplication operations (entity-set based).

    Specify which entity sets to duplicate members from. The new matrix
    will have the same structure but only the selected entity sets will
    be populated with members.
    """

    name: str
    description: Optional[str] = None
    entity_set_ids: List[int]  # Which entity sets to copy members from
    template_variable_overrides: Optional[List[TemplateVariableOverride]] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class MatrixDuplicateResponse(BaseModel):
    """Response schema for matrix duplication operations."""

    original_matrix_id: int
    duplicate_matrix_id: int
    entity_sets_duplicated: Dict[int, int]  # {source_entity_set_id: members_count}
    cells_created: int
    message: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class MatrixCellsBatchRequest(BaseModel):
    """Request schema for batch fetching matrix cells (entity-ref based).

    Frontend provides entity_set_filters to specify which entities to fetch cells for.
    Each filter specifies an entity_set_id and list of entity_ids.
    """

    entity_set_filters: List[EntitySetFilter]

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class MatrixStatsResponse(BaseModel):
    """Response schema for matrix cell statistics."""

    total_cells: int
    completed: int
    processing: int
    pending: int
    failed: int
    # Document extraction stats (separate from QA cell stats)
    documents_pending_extraction: int = 0
    documents_failed_extraction: int = 0

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )
