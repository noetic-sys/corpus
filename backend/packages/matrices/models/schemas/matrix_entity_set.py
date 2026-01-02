"""
API response schemas for matrix entity sets.

These schemas are used for the entity sets API endpoint which provides
entity set information to the frontend for constructing tile queries.
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel

from packages.matrices.models.domain.matrix_enums import EntityType, MatrixType


class EntitySetMemberResponse(BaseModel):
    """Response schema for entity set member.

    Contains the member ID and the actual entity ID (document/question ID).
    """

    id: int = Field(description="Entity set member ID")
    entity_set_id: int = Field(
        description="ID of the entity set this member belongs to"
    )
    entity_type: EntityType = Field(description="Type of entity (DOCUMENT or QUESTION)")
    entity_id: int = Field(
        description="ID of the actual entity (document ID or question ID)"
    )
    member_order: int = Field(description="Order of this member within the entity set")
    label: Optional[str] = Field(
        default=None, description="Optional label for this member in this context"
    )
    created_at: datetime = Field(description="Timestamp when member was created")

    model_config = {
        "from_attributes": True,
        "alias_generator": to_camel,
        "populate_by_name": True,
    }


class EntitySetMemberLabelUpdate(BaseModel):
    """Request schema for updating entity set member label."""

    label: Optional[str] = Field(description="New label value (null to clear)")


class EntitySetResponse(BaseModel):
    """Response schema for entity set with its members.

    Contains all information needed by the frontend to construct entity_set_filters.
    """

    id: int = Field(description="Entity set ID")
    matrix_id: int = Field(description="ID of the matrix this entity set belongs to")
    name: str = Field(
        description="Name of the entity set (e.g., 'documents', 'questions')"
    )
    entity_type: EntityType = Field(description="Type of entities in this set")
    created_at: datetime = Field(description="Timestamp when entity set was created")
    members: List[EntitySetMemberResponse] = Field(
        description="List of members in this entity set", default_factory=list
    )

    model_config = {
        "from_attributes": True,
        "alias_generator": to_camel,
        "populate_by_name": True,
    }


class MatrixEntitySetsResponse(BaseModel):
    """Response schema for all entity sets in a matrix.

    This provides complete entity set information for a matrix,
    allowing the frontend to:
    1. Determine matrix dimensionality
    2. Construct entity_set_filters for tile queries
    3. Map entity IDs to entity set member IDs
    """

    matrix_id: int = Field(description="ID of the matrix")
    matrix_type: MatrixType = Field(
        description="Type of the matrix (STANDARD, CROSS_CORRELATION, etc.)"
    )
    entity_sets: List[EntitySetResponse] = Field(
        description="List of all entity sets in the matrix", default_factory=list
    )

    model_config = {
        "from_attributes": True,
        "alias_generator": to_camel,
        "populate_by_name": True,
    }
