"""
Database entity for subscriptions.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class SubscriptionEntity(Base):
    """
    Company subscription database entity.

    Stores subscription tier, status, and external platform IDs.
    One-to-one relationship with companies table.
    """

    __tablename__ = "subscriptions"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    company_id = Column(
        BigIntegerType,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Subscription details
    tier = Column(
        String(50), nullable=False, index=True
    )  # standard, professional, enterprise
    status = Column(
        String(50), nullable=False, index=True
    )  # active, past_due, suspended, cancelled

    # External platform IDs
    # Note: stripe_customer_id lives on companies table (represents company identity)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True, index=True)

    # Payment provider
    payment_provider = Column(String(50), nullable=False, server_default="stripe")

    # Billing cycle
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)

    # Lifecycle timestamps
    started_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    suspended_at = Column(DateTime(timezone=True), nullable=True)

    # Standard timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_subscription_status_tier", "status", "tier"),
        Index("idx_subscription_period_end", "current_period_end"),
    )
