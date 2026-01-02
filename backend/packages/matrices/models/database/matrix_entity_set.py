"""
SQLAlchemy entities for the entity set model.

These tables enable N-dimensional matrix support through flexible entity sets
and role-based cell entity references.
"""

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, Index
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class MatrixEntitySetEntity(Base):
    """Entity set within a matrix.

    An entity set is a named collection of entities (documents or questions).
    For standard matrices: typically 2 sets (documents, questions).
    For correlation matrices: typically 2 sets (documents used in multiple roles, questions).
    """

    __tablename__ = "matrix_entity_sets"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    matrix_id = Column(
        BigIntegerType,
        ForeignKey("matrices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    name = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)  # 'document' | 'question'
    deleted = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_entity_set_matrix", "matrix_id"),)

    # Relationships commented out per convention
    # matrix = relationship("MatrixEntity", back_populates="entity_sets")
    # members = relationship(
    #     "MatrixEntitySetMemberEntity",
    #     back_populates="entity_set",
    #     cascade="all, delete-orphan",
    #     lazy="select"
    # )


class MatrixEntitySetMemberEntity(Base):
    """Member of an entity set.

    Links an entity (document or question) to an entity set with ordering.
    Multiple members can reference the same entity_id across different sets.
    """

    __tablename__ = "matrix_entity_set_members"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    entity_set_id = Column(
        BigIntegerType,
        ForeignKey("matrix_entity_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    entity_type = Column(String, nullable=False)  # 'document' | 'question'
    entity_id = Column(
        BigIntegerType, nullable=False
    )  # References documents.id or questions.id
    member_order = Column(Integer, nullable=False, default=0)
    label = Column(String, nullable=True)  # Optional display label for this member
    deleted = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_member_entity_set", "entity_set_id"),
        Index("idx_member_lookup", "entity_set_id", "entity_type", "entity_id"),
    )

    # Relationships commented out per convention
    # entity_set = relationship("MatrixEntitySetEntity", back_populates="members")


class MatrixCellEntityReferenceEntity(Base):
    """Entity reference for a matrix cell - the N-dimensional coordinate system.

    Each row represents ONE dimension of a cell's coordinate.
    The 'role' field IS the axis identifier (e.g., 'left', 'right', 'question').

    Standard cell (2D):
    - 2 rows: one with role='document', one with role='question'

    Correlation cell (3D):
    - 3 rows: role='left', role='right', role='question'

    Role MUST be included in all queries for proper index usage and axis identification.
    """

    __tablename__ = "matrix_cell_entity_refs"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    matrix_id = Column(
        BigIntegerType,
        ForeignKey("matrices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    matrix_cell_id = Column(
        BigIntegerType,
        ForeignKey("matrix_cells.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_set_id = Column(
        BigIntegerType,
        ForeignKey("matrix_entity_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_set_member_id = Column(
        BigIntegerType,
        ForeignKey("matrix_entity_set_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    role = Column(
        String, nullable=False
    )  # REQUIRED: 'left' | 'right' | 'document' | 'question' - this IS the axis identifier
    entity_order = Column(Integer, nullable=False, default=0)
    deleted = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_cell_entity_lookup", "matrix_cell_id", "role"),
        Index(
            "idx_entity_set_filter",
            "matrix_id",
            "entity_set_id",
            "entity_set_member_id",
            "role",
        ),
    )

    # Relationships commented out per convention
    # matrix = relationship("MatrixEntity")
    # matrix_cell = relationship("MatrixCellEntity")
    # entity_set = relationship("MatrixEntitySetEntity")
    # entity_set_member = relationship("MatrixEntitySetMemberEntity")
