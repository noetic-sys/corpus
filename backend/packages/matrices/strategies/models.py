"""
Shared models for strategy pattern.

These models are used by all strategies to maintain consistency.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field

from packages.matrices.models.domain.matrix_enums import (
    EntityType,
    CellType,
    MatrixType,
)
from packages.matrices.models.domain.matrix_entity_set import (
    DocumentContext,
    QuestionContext,
    EntityReference,
)


class EntitySetDefinition(BaseModel):
    """Defines an entity set for matrix creation.

    Strategies return a list of these to declare what entity sets
    their matrix type requires.

    Example:
        Standard matrix returns:
        [
            EntitySetDefinition(name="Documents", entity_type=EntityType.DOCUMENT),
            EntitySetDefinition(name="Questions", entity_type=EntityType.QUESTION),
        ]

        Generic correlation returns:
        [
            EntitySetDefinition(name="Left Documents", entity_type=EntityType.DOCUMENT),
            EntitySetDefinition(name="Right Documents", entity_type=EntityType.DOCUMENT),
            EntitySetDefinition(name="Questions", entity_type=EntityType.QUESTION),
        ]
    """

    name: str
    entity_type: EntityType
    description: Optional[str] = None


class CellDataContext(BaseModel):
    """Standardized cell data format for QA processing.

    All strategies return this from load_cell_data(). Contains everything
    needed for template resolution and AI processing.

    Uses properly typed models instead of dictionaries:
    - DocumentContext: document_id, filename, content, role, entity_ref
    - QuestionContext: question_id, question_text, question_type_id, min_answers, max_answers, entity_ref
    - EntityReference: entity_set_id, entity_set_member_id, entity_type, entity_id, role
    """

    cell_id: int
    matrix_id: int
    cell_type: CellType
    matrix_type: MatrixType

    # Loaded entities (properly typed)
    documents: List[DocumentContext]
    question: QuestionContext

    # Entity refs for template resolution (already includes role, entity_id, etc.)
    # Note: entity_refs are also embedded in DocumentContext and QuestionContext,
    # but we keep this list for convenience in template resolution
    entity_refs: List[EntityReference]

    model_config = {"from_attributes": True}


class MatrixStructureMetadata(BaseModel):
    """Metadata about matrix structure for understanding cell data.

    Strategies return this to help agents understand:
    - How the matrix is organized (entity sets, dimensionality)
    - What roles entities play in cells (DOCUMENT, LEFT, RIGHT, QUESTION)
    - What system placeholders mean (@{{LEFT}}, @{{RIGHT}}, etc.)
    - How to interpret cell data when fetching from the API

    This is NOT about output formatting - the user provides their own templates.
    This is about understanding the DATA STRUCTURE of the matrix.

    Example for CrossCorrelationStrategy:
        MatrixStructureMetadata(
            explanation="Cross-correlation matrix: document pairs × questions...",
            roles_explanation={
                "LEFT": "First document in the comparison pair",
                "RIGHT": "Second document in the comparison pair (from same set)",
                "QUESTION": "Comparison question"
            },
            system_placeholders={
                "@{{LEFT}}": "References the LEFT document in questions",
                "@{{RIGHT}}": "References the RIGHT document in questions"
            },
            cell_structure="Each cell contains: LEFT document, RIGHT document, QUESTION, ANSWER"
        )
    """

    explanation: str = Field(
        ...,
        description="How this matrix type is structured (dimensionality, entity sets)",
    )

    roles_explanation: Dict[str, str] = Field(
        ...,
        description="What each entity role means (DOCUMENT, LEFT, RIGHT, QUESTION)",
    )

    system_placeholders: Dict[str, str] = Field(
        ...,
        description="System placeholders used in questions (@{{LEFT}}, @{{RIGHT}}), NOT for user templates",
    )

    cell_structure: str = Field(
        ...,
        description="Description of what data is in each cell",
    )
