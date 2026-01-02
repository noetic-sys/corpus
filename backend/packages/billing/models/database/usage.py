"""
Database entity for usage events.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Index, JSON, Integer
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class UsageEventEntity(Base):
    """
    Usage event database entity.

    Records every billable action for audit trail and analytics.
    High volume table - partitioned by created_at in production.
    """

    __tablename__ = "usage_events"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    company_id = Column(
        BigIntegerType,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        BigIntegerType,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Event details
    event_type = Column(
        String(50), nullable=False, index=True
    )  # cell_operation, agentic_qa, workflow, storage_upload

    # Quantity of operations in this event (for batched tracking)
    # e.g., 500 cells created = quantity=500
    # Default 1 for single operations
    quantity = Column(Integer, nullable=False, server_default="1")

    # File size in bytes for storage uploads (denormalized for fast aggregation)
    # NULL for non-storage events
    file_size_bytes = Column(Integer, nullable=True, index=True)

    # Event-specific metadata (JSON for flexibility)
    # Examples:
    # - cell_operation: {matrix_id: 123}
    # - storage_upload: {document_id: 123, filename: "doc.pdf"}
    event_metadata = Column("metadata", JSON, nullable=False, server_default="{}")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Composite indexes for analytics queries
    __table_args__ = (
        Index("idx_usage_company_type_date", "company_id", "event_type", "created_at"),
        Index("idx_usage_user_date", "user_id", "created_at"),
    )
