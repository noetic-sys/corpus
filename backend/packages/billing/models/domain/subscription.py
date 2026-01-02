"""
Domain models for subscriptions.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from packages.billing.models.domain.enums import (
    SubscriptionStatus,
    SubscriptionTier,
    PaymentProvider,
)


class Subscription(BaseModel):
    """
    Company subscription domain model.

    Represents a company's active subscription including:
    - Tier (Standard/Professional/Enterprise)
    - Status (Active/Past Due/Suspended/Cancelled)
    - Billing cycle dates
    - External IDs for Stripe
    """

    id: int
    company_id: int

    # Subscription details
    tier: SubscriptionTier
    status: SubscriptionStatus

    # External platform IDs
    # Note: stripe_customer_id lives on Company (represents company identity)
    stripe_subscription_id: Optional[str] = None

    # Payment
    payment_provider: PaymentProvider = PaymentProvider.STRIPE

    # Billing cycle
    current_period_start: datetime
    current_period_end: datetime

    # Lifecycle dates
    started_at: datetime
    cancelled_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None

    # Metadata
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    def has_access(self) -> bool:
        """Check if subscription allows product access."""
        return self.status.has_access()

    def is_billable(self) -> bool:
        """Check if subscription should be billed."""
        return self.status.is_billable()

    def days_until_renewal(self) -> int:
        """Get number of days until next billing cycle."""
        delta = self.current_period_end - datetime.utcnow()
        return max(0, delta.days)


class SubscriptionCreateModel(BaseModel):
    """Model for creating a new subscription."""

    company_id: int
    tier: SubscriptionTier
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    payment_provider: PaymentProvider = PaymentProvider.STRIPE
    current_period_start: datetime = Field(default_factory=datetime.utcnow)
    current_period_end: datetime  # Must be provided

    # Optional external IDs
    stripe_subscription_id: Optional[str] = None


class SubscriptionUpdateModel(BaseModel):
    """Model for updating a subscription."""

    tier: Optional[str] = None
    status: Optional[str] = None

    stripe_subscription_id: Optional[str] = None

    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None

    cancelled_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None

    @field_validator("tier", mode="before")
    @classmethod
    def validate_tier(cls, v):
        if isinstance(v, SubscriptionTier):
            return v.value
        return v

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if isinstance(v, SubscriptionStatus):
            return v.value
        return v
