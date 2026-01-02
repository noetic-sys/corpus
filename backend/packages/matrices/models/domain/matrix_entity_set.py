"""
Domain models for entity sets and cell entity references.

These models support N-dimensional matrix coordinates through flexible entity sets
and role-based entity references.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, TypeVar, Generic
from pydantic import BaseModel

from packages.matrices.models.domain.matrix_enums import EntityType, EntityRole


# ============================================================================
# Entity Set Models
# ============================================================================


class MatrixEntitySetModel(BaseModel):
    """Domain model for matrix entity sets."""

    id: int
    matrix_id: int
    company_id: int
    name: str
    entity_type: EntityType
    created_at: datetime

    model_config = {"from_attributes": True}


class MatrixEntitySetCreateModel(BaseModel):
    """Model for creating a matrix entity set."""

    matrix_id: int
    company_id: int
    name: str
    entity_type: EntityType


class MatrixEntitySetMemberModel(BaseModel):
    """Domain model for entity set members."""

    id: int
    entity_set_id: int
    company_id: int
    entity_type: EntityType
    entity_id: int
    member_order: int
    label: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MatrixEntitySetMemberCreateModel(BaseModel):
    """Model for creating an entity set member."""

    entity_set_id: int
    company_id: int
    entity_type: EntityType
    entity_id: int
    member_order: int = 0
    label: Optional[str] = None


# ============================================================================
# Cell Entity Reference Models
# ============================================================================


class MatrixCellEntityReferenceModel(BaseModel):
    """Domain model for matrix cell entity references.

    Each reference represents ONE dimension of a cell's N-dimensional coordinate.
    The 'role' field IS the axis identifier.
    """

    id: int
    matrix_id: int
    matrix_cell_id: int
    entity_set_id: int
    entity_set_member_id: int
    company_id: int
    role: EntityRole  # REQUIRED - this IS the axis identifier
    entity_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class MatrixCellEntityReferenceCreateModel(BaseModel):
    """Model for creating a matrix cell entity reference."""

    matrix_id: int
    matrix_cell_id: int
    entity_set_id: int
    entity_set_member_id: int
    company_id: int
    role: EntityRole  # REQUIRED
    entity_order: int = 0


# ============================================================================
# Entity Reference (used by strategies and QA processing)
# ============================================================================


class EntityReference(BaseModel):
    """Reference to an entity for cell creation and QA processing.

    Used by:
    - Cell creation strategies to specify which entities belong to a cell
    - QA worker to load the correct documents and questions
    - Frontend to map cells to grid coordinates
    """

    entity_set_id: int
    entity_set_member_id: int
    entity_type: EntityType
    entity_id: int
    role: EntityRole  # REQUIRED - identifies which axis this entity is on
    entity_order: int = 0


# ============================================================================
# QA Processing Context Models
# ============================================================================


class DocumentContext(BaseModel):
    """Document context for QA processing.

    Contains all information needed to process a document in a cell,
    including its role (DOCUMENT, LEFT, RIGHT, PRIMARY, SECONDARY).
    """

    document_id: int
    filename: str
    content: str  # SecretStr in actual implementation if needed
    role: EntityRole
    entity_ref: EntityReference

    model_config = {"from_attributes": True}


class QuestionContext(BaseModel):
    """Question context for QA processing."""

    question_id: int
    question_text: str
    question_type_id: Optional[int] = None
    min_answers: int = 1
    max_answers: Optional[int] = 1
    entity_ref: EntityReference

    model_config = {"from_attributes": True}


# ============================================================================
# Strategy-specific Document Containers
# ============================================================================


class StandardDocuments(BaseModel):
    """Document container for standard matrices: single document."""

    document: DocumentContext


class CorrelationDocuments(BaseModel):
    """Document container for correlation matrices: left + right documents."""

    left: DocumentContext
    right: DocumentContext


# ============================================================================
# Generic Cell Context (typed by strategy)
# ============================================================================


TDocuments = TypeVar("TDocuments", StandardDocuments, CorrelationDocuments)


class CellContext(BaseModel, Generic[TDocuments]):
    """Complete context for processing a matrix cell.

    Generic over document container type for compile-time type safety.
    Strategies return strongly-typed contexts:
    - StandardMatrixStrategy returns CellContext[StandardDocuments]
    - CrossCorrelationStrategy returns CellContext[CorrelationDocuments]
    """

    cell_id: int
    matrix_id: int
    documents: TDocuments
    question: QuestionContext

    model_config = {"from_attributes": True}


# Type aliases for clarity
StandardCellContext = CellContext[StandardDocuments]
CorrelationCellContext = CellContext[CorrelationDocuments]
