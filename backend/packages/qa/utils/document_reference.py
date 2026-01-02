"""Shared document reference model used by strategies and workers."""

from pydantic import BaseModel
from packages.matrices.models.domain.matrix_enums import EntityRole


class DocumentReference(BaseModel):
    """Document reference with its role in the cell."""

    document_id: int
    role: EntityRole  # DOCUMENT, LEFT, or RIGHT
