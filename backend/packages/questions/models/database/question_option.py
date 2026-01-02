from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class QuestionOptionSetEntity(Base):
    __tablename__ = "question_option_sets"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    question_id = Column(
        BigIntegerType,
        ForeignKey("questions.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # question = relationship("QuestionEntity", back_populates="option_set")
    # options = relationship(
    #    "QuestionOptionEntity",
    #    back_populates="option_set",
    #    cascade="all, delete-orphan",
    #    lazy="select",
    # )


class QuestionOptionEntity(Base):
    __tablename__ = "question_options"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    option_set_id = Column(
        BigIntegerType,
        ForeignKey("question_option_sets.id"),
        nullable=False,
        index=True,
    )
    value = Column(String, nullable=False)  # The actual option text
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # option_set = relationship("QuestionOptionSetEntity", back_populates="options")
