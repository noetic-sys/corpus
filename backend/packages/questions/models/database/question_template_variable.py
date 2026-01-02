from sqlalchemy import Column, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class QuestionTemplateVariableEntity(Base):
    __tablename__ = "question_template_variables"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    question_id = Column(
        BigIntegerType, ForeignKey("questions.id"), nullable=False, index=True
    )
    template_variable_id = Column(
        BigIntegerType,
        ForeignKey("matrix_template_variables.id"),
        nullable=False,
        index=True,
    )
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    deleted = Column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # question = relationship("QuestionEntity", back_populates="template_variables")
    # template_variable = relationship(
    #    "MatrixTemplateVariableEntity", back_populates="questions"
    # )
