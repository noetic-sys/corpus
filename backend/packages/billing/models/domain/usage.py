"""
Domain models for usage tracking and quotas.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from packages.billing.models.domain.enums import (
    SubscriptionTier,
    UsageEventType,
)


class QuotaCheck(BaseModel):
    """
    Result of a quota enforcement check.

    Used to determine if an operation is allowed and provide
    user-friendly feedback about usage limits.
    """

    allowed: bool
    metric_name: str
    current_usage: int
    limit: int
    remaining: int
    percentage_used: float
    warning_threshold_reached: bool  # True if >= 80% used

    # For frontend display
    period_type: str  # "monthly"
    period_end: datetime

    def get_user_message(self) -> Optional[str]:
        """Get user-friendly message about quota status."""
        if not self.allowed:
            return f"Monthly {self.metric_name} limit reached ({self.limit:,}). Upgrade to continue."

        if self.warning_threshold_reached:
            return f"You've used {self.percentage_used:.0f}% of your monthly {self.metric_name} quota ({self.current_usage:,}/{self.limit:,})."

        return None


class UsageStats(BaseModel):
    """
    Complete usage statistics for a company.

    Aggregates all usage metrics for display in dashboard.
    """

    company_id: int
    tier: SubscriptionTier

    # Monthly usage
    cell_operations: int
    cell_operations_limit: int
    agentic_qa: int
    agentic_qa_limit: int
    workflows: int
    workflows_limit: int
    storage_bytes: int
    storage_bytes_limit: int
    agentic_chunking: int
    agentic_chunking_limit: int
    documents: int
    documents_limit: int

    # Billing period
    period_start: datetime
    period_end: datetime

    def get_quota_percentage(self, metric: str) -> float:
        """Get percentage used for a given metric."""
        usage_map = {
            "cell_operations": (self.cell_operations, self.cell_operations_limit),
            "agentic_qa": (self.agentic_qa, self.agentic_qa_limit),
            "workflows": (self.workflows, self.workflows_limit),
            "storage": (self.storage_bytes, self.storage_bytes_limit),
            "agentic_chunking": (self.agentic_chunking, self.agentic_chunking_limit),
            "documents": (self.documents, self.documents_limit),
        }

        if metric not in usage_map:
            return 0.0

        current, limit = usage_map[metric]
        if limit == 0:
            return 0.0

        return (current / limit) * 100


class UsageEvent(BaseModel):
    """
    Individual usage event record.

    Tracks every billable action for audit trail and analytics.
    """

    id: int
    company_id: int
    user_id: Optional[int] = None

    event_type: UsageEventType

    # Quantity of operations in this event (for batched tracking)
    quantity: int = 1

    # File size in bytes (for storage uploads, NULL for other events)
    file_size_bytes: Optional[int] = None

    # Event-specific metadata
    event_metadata: dict

    created_at: datetime

    class Config:
        from_attributes = True


class UsageEventCreateModel(BaseModel):
    """Model for creating a usage event."""

    company_id: int
    user_id: Optional[int] = None
    event_type: UsageEventType
    quantity: int = 1
    file_size_bytes: Optional[int] = None
    event_metadata: dict = {}


class QuotaReservationResult(BaseModel):
    """Result of an atomic quota check and reservation."""

    reserved: bool
    usage_event_id: Optional[int] = None
    current_usage: int
    limit: int
    tier: SubscriptionTier

    class Config:
        from_attributes = True
