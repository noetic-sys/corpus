from sqlalchemy import Column, Text, ForeignKey, DateTime, JSON, Boolean, Integer
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class QuestionEntity(Base):
    __tablename__ = "questions"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    question_text = Column(Text, nullable=False)
    matrix_id = Column(
        BigIntegerType, ForeignKey("matrices.id"), nullable=False, index=True
    )
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    question_type_id = Column(
        BigIntegerType,
        ForeignKey("question_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        server_default="1",  # Default to SHORT_ANSWER (id=1)
    )
    ai_model_id = Column(
        BigIntegerType,
        ForeignKey("ai_models.id"),
        nullable=True,
        index=True,
    )  # AI model selection per question
    ai_config_override = Column(
        JSON, nullable=True
    )  # Per-question AI config overrides (temperature, max_tokens)
    label = Column(Text, nullable=True)
    min_answers = Column(Integer, nullable=False, default=1, server_default="1")
    max_answers = Column(Integer, nullable=True)
    use_agent_qa = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )  # Whether to use agent-based QA for this question
    deleted = Column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # matrix = relationship("MatrixEntity", back_populates="questions")
    # question_type = relationship("QuestionTypeEntity", back_populates="questions")
    # ai_model = relationship("AIModelEntity", back_populates="questions")
    # option_set = relationship(
    #    "QuestionOptionSetEntity",
    #    back_populates="question",
    #    uselist=False,
    #    cascade="all, delete-orphan",
    #    lazy="select",
    # )
    # matrix_cells = relationship(
    #    "MatrixCellEntity",
    #    back_populates="question",
    #    cascade="all, delete-orphan",
    #    lazy="select",
    # )
    # template_variables = relationship(
    #    "QuestionTemplateVariableEntity",
    #    back_populates="question",
    #    cascade="all, delete-orphan",
    #    lazy="select",
    # )
