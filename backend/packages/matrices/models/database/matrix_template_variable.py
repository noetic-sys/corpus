from sqlalchemy import Column, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class MatrixTemplateVariableEntity(Base):
    __tablename__ = "matrix_template_variables"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    template_string = Column(Text, nullable=False)
    value = Column(Text, nullable=False)
    matrix_id = Column(
        BigIntegerType, ForeignKey("matrices.id"), nullable=False, index=True
    )
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    deleted = Column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # matrix = relationship("MatrixEntity", back_populates="template_variables")
    # questions = relationship(
    #    "QuestionTemplateVariableEntity",
    #    back_populates="template_variable",
    #    cascade="all, delete-orphan",
    #    lazy="select",
    # )
