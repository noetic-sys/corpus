from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func


from common.db.base import Base, BigIntegerType
from packages.matrices.models.domain.matrix import MatrixCellStatus
from packages.matrices.models.domain.matrix_enums import MatrixType


class MatrixEntity(Base):
    __tablename__ = "matrices"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    workspace_id = Column(
        BigIntegerType, ForeignKey("workspaces.id"), nullable=False, index=True
    )
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    matrix_type = Column(
        String,
        nullable=False,
        default=MatrixType.STANDARD.value,
        server_default=MatrixType.STANDARD.value,
        index=True,
    )
    deleted = Column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # workspace = relationship("WorkspaceEntity", back_populates="matrices")
    # questions = relationship(
    #    "QuestionEntity",
    #    back_populates="matrix",
    #    cascade="all, delete-orphan",
    #    lazy="select",
    # )
    # matrix_cells = relationship(
    #    "MatrixCellEntity",
    #    back_populates="matrix",
    #    cascade="all, delete-orphan",
    #    lazy="select",
    # )
    # template_variables = relationship(
    #    "MatrixTemplateVariableEntity",
    #    back_populates="matrix",
    #    cascade="all, delete-orphan",
    #    lazy="select",
    # )


class MatrixCellEntity(Base):
    __tablename__ = "matrix_cells"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)

    matrix_id = Column(
        BigIntegerType, ForeignKey("matrices.id"), nullable=False, index=True
    )
    # document_id and question_id DROPPED - using entity_refs instead
    current_answer_set_id = Column(
        BigIntegerType, ForeignKey("answer_sets.id"), nullable=True, index=True
    )
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    status = Column(String, default=MatrixCellStatus.PENDING.value, nullable=False)
    cell_type = Column(
        String, nullable=False
    )  # 'standard' | 'correlation' - REQUIRED for QA processing
    cell_signature = Column(
        String, nullable=False
    )  # Hash of sorted entity refs - MUST be computed by application
    deleted = Column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # matrix = relationship("MatrixEntity", back_populates="matrix_cells")
    # document = relationship("DocumentEntity", back_populates="matrix_cells")
    # question = relationship("QuestionEntity", back_populates="matrix_cells")
    # current_answer_set = relationship(
    #    "AnswerSetEntity", foreign_keys=[current_answer_set_id], lazy="select"
    # )
    # answer_sets = relationship(
    #    "AnswerSetEntity",
    #    back_populates="matrix_cell",
    #    foreign_keys="[AnswerSetEntity.matrix_cell_id]",
    #    cascade="all, delete-orphan",
    #    lazy="select",
    # )
    # qa_jobs = relationship(
    #    "QAJobEntity",
    #    back_populates="matrix_cell",
    #    cascade="all, delete-orphan",
    #    lazy="select",
    # )
