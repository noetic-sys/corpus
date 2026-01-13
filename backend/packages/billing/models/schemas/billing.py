"""
API schemas for billing operations.

Request and response models for billing endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from pydantic.alias_generators import to_camel

from packages.billing.models.domain.enums import SubscriptionTier, SubscriptionStatus


# ============================================================================
# Checkout Schemas
# ============================================================================


class CheckoutSessionRequest(BaseModel):
    """Request to create a checkout session."""

    tier: SubscriptionTier
    success_url: HttpUrl
    cancel_url: HttpUrl
    billing_email: Optional[str] = None
    trial_period_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=90,
        description="Number of trial days (1-90). If not provided, no trial period.",
    )


class CheckoutSessionResponse(BaseModel):
    """Response with checkout URL."""

    checkout_url: str = Field(..., description="Stripe checkout session URL")


# ============================================================================
# Portal Schemas
# ============================================================================


class PortalSessionRequest(BaseModel):
    """Request to create a customer portal session."""

    return_url: HttpUrl


class PortalSessionResponse(BaseModel):
    """Response with portal URL."""

    portal_url: str = Field(..., description="Stripe customer portal URL")


# ============================================================================
# Subscription Schemas
# ============================================================================


class SubscriptionStatusResponse(BaseModel):
    """Current subscription status."""

    company_id: int
    tier: SubscriptionTier
    status: SubscriptionStatus
    has_access: bool = Field(..., description="Whether company has product access")
    current_period_start: datetime
    current_period_end: datetime
    cancelled_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None


# ============================================================================
# Usage Schemas
# ============================================================================


class QuotaStatusResponse(BaseModel):
    """Quota status for a specific metric."""

    metric_name: str
    current_usage: int
    limit: int
    remaining: int
    percentage_used: float
    warning_threshold_reached: bool = Field(
        ..., description="True if usage is >= 80% of limit"
    )
    period_type: str = Field(..., description="'daily' or 'monthly'")
    period_end: datetime


class UsageStatsResponse(BaseModel):
    """Complete usage statistics for the 5 quota types."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    company_id: int
    tier: SubscriptionTier

    # Cell Operations
    cell_operations: int
    cell_operations_limit: int
    cell_operations_percentage: float = Field(
        ..., description="Percentage of monthly cell operations quota used"
    )

    # Agentic QA
    agentic_qa: int
    agentic_qa_limit: int
    agentic_qa_percentage: float = Field(
        ..., description="Percentage of monthly agentic QA quota used"
    )

    # Workflows
    workflows: int
    workflows_limit: int
    workflows_percentage: float = Field(
        ..., description="Percentage of monthly workflows quota used"
    )

    # Storage (bytes)
    storage_bytes: int
    storage_bytes_limit: int
    storage_bytes_percentage: float = Field(
        ..., description="Percentage of monthly storage quota used"
    )

    # Agentic Chunking (AI document processing)
    agentic_chunking: int
    agentic_chunking_limit: int
    agentic_chunking_percentage: float = Field(
        ..., description="Percentage of monthly AI document processing quota used"
    )

    # Documents (upload count)
    documents: int
    documents_limit: int
    documents_percentage: float = Field(
        ..., description="Percentage of monthly document upload quota used"
    )

    # Period
    period_start: datetime
    period_end: datetime


# ============================================================================
# Tier Management Schemas
# ============================================================================


class UpgradeTierRequest(BaseModel):
    """Request to upgrade subscription tier."""

    new_tier: SubscriptionTier


class UpgradeTierResponse(BaseModel):
    """Response after tier upgrade."""

    success: bool
    message: str
    new_tier: SubscriptionTier
    old_tier: SubscriptionTier


# ============================================================================
# Cancellation Schemas
# ============================================================================


class CancelSubscriptionResponse(BaseModel):
    """Response after subscription cancellation."""

    success: bool
    message: str
    cancelled_at: datetime
    access_until: datetime = Field(
        ..., description="Date until which company retains access"
    )
