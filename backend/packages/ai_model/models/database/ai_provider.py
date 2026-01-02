from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class AIProviderEntity(Base):
    __tablename__ = "ai_providers"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    name = Column(
        String, unique=True, nullable=False, index=True
    )  # e.g., "openai", "anthropic"
    display_name = Column(String, nullable=False)  # e.g., "OpenAI", "Anthropic"
    enabled = Column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    # models = relationship(
    #    "AIModelEntity",
    #    back_populates="provider",
    #    cascade="all, delete-orphan",
    #    lazy="select",
    # )
