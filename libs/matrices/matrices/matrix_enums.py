"""
Enum definitions for the entity set matrix model.

These enums provide type safety across the entire matrix system:
- MatrixType: Determines cell creation strategy
- CellType: Determines QA processing behavior
- EntityType: Type of entity in entity sets
- EntityRole: Role that entities play in matrix cells (the axis identifier)
- MatrixCellStatus: Processing status of cells
"""

from enum import Enum


class MatrixType(str, Enum):
    """Types of matrices - determines cell creation strategy."""

    STANDARD = "standard"
    CROSS_CORRELATION = "cross_correlation"
    GENERIC_CORRELATION = "generic_correlation"
    SYNOPSIS = "synopsis"


class CellType(str, Enum):
    """Types of matrix cells - determines QA processing behavior."""

    STANDARD = "standard"
    CORRELATION = "correlation"
    SYNOPSIS = "synopsis"


class EntityType(str, Enum):
    """Types of entities in entity sets."""

    DOCUMENT = "document"
    QUESTION = "question"


class EntityRole(str, Enum):
    """Roles that entities can play in a matrix cell.

    This IS the axis identifier in N-dimensional matrices.
    Each role represents a distinct dimension/axis.
    """

    DOCUMENT = "document"  # Standard matrix document
    QUESTION = "question"  # Standard matrix question
    LEFT = "left"  # Left document in correlation
    RIGHT = "right"  # Right document in correlation
    PRIMARY = "primary"  # Primary document in generic correlation
    SECONDARY = "secondary"  # Secondary document in generic correlation


class MatrixCellStatus(str, Enum):
    """Status of matrix cell processing."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
