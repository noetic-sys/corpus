from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class QuestionTypeEntity(Base):
    __tablename__ = "question_types"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    validation_schema = Column(JSON, nullable=True)  # JSON schema for validation rules
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # questions = relationship(
    #    "QuestionEntity",
    #    back_populates="question_type",
    #    lazy="select",
    # )
    # answer_sets = relationship(
    #    "AnswerSetEntity",
    #    back_populates="question_type",
    #    lazy="select",
    # )
