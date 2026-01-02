from sqlalchemy import Column, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class ConversationEntity(Base):
    __tablename__ = "conversations"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    title = Column(Text, nullable=True)
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    extra_data = Column(JSON, nullable=True)  # Additional conversation metadata
    ai_model_id = Column(
        BigIntegerType,
        ForeignKey("ai_models.id"),
        nullable=True,
        index=True,
    )  # AI model selection for this conversation
    is_active = Column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )
    deleted = Column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
