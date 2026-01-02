from sqlalchemy import Column, Boolean, DateTime, ForeignKey, Float
from common.db.base import Base, BigIntegerType
from sqlalchemy.sql import func


class AnswerSetEntity(Base):
    __tablename__ = "answer_sets"

    id = Column(BigIntegerType, primary_key=True, index=True)
    matrix_cell_id = Column(
        BigIntegerType, ForeignKey("matrix_cells.id"), nullable=False, index=True
    )
    question_type_id = Column(
        BigIntegerType, ForeignKey("question_types.id"), nullable=False
    )
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    answer_found = Column(Boolean, default=False, nullable=False)
    confidence = Column(Float, default=1.0, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    # matrix_cell = relationship(
    #    "MatrixCellEntity", back_populates="answer_sets", foreign_keys=[matrix_cell_id]
    # )
    # question_type = relationship(
    #    "QuestionTypeEntity", back_populates="answer_sets", lazy="select"
    # )
    # answers = relationship(
    #    "AnswerEntity", back_populates="answer_set", cascade="all, delete-orphan"
    # )
