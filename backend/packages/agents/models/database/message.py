from sqlalchemy import Column, Text, DateTime, JSON, ForeignKey, String, Integer
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class MessageEntity(Base):
    __tablename__ = "messages"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(
        BigIntegerType,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    role = Column(
        String(20), nullable=False, index=True
    )  # user, assistant, system, tool
    content = Column(Text, nullable=True)  # Text content of the message
    tool_calls = Column(JSON, nullable=True)  # Tool calls made by assistant
    tool_call_id = Column(
        String(255), nullable=True, index=True
    )  # ID for tool responses
    sequence_number = Column(
        Integer, nullable=False, index=True
    )  # Order within conversation
    permission_mode = Column(
        String(20), nullable=False, default="read", index=True
    )  # Permission mode: 'read' or 'write'
    extra_data = Column(JSON, nullable=True)  # Additional message metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
