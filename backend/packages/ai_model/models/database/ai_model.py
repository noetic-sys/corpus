from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Float, Integer
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class AIModelEntity(Base):
    __tablename__ = "ai_models"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    provider_id = Column(
        BigIntegerType, ForeignKey("ai_providers.id"), nullable=False, index=True
    )
    model_name = Column(
        String, nullable=False, index=True
    )  # e.g., "gpt-4", "claude-3-sonnet-20240229"
    display_name = Column(String, nullable=False)  # e.g., "GPT-4", "Claude 3 Sonnet"
    default_temperature = Column(Float, nullable=False, default=0.7)
    default_max_tokens = Column(Integer, nullable=True)  # None means provider default
    enabled = Column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    # provider = relationship("AIProviderEntity", back_populates="models")
    # questions = relationship(
    #    "QuestionEntity",
    #    back_populates="ai_model",
    #    lazy="select",
    # )
