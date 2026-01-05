"""
Billing enums - strongly typed enumerations for subscription and billing states.
"""

from enum import Enum


class SubscriptionStatus(str, Enum):
    """
    Subscription status lifecycle.

    Flow: active -> past_due -> suspended -> cancelled
    """

    ACTIVE = "active"  # Subscription is active and paid
    PAST_DUE = "past_due"  # Payment failed, in grace period (7 days)
    SUSPENDED = "suspended"  # Grace period expired, access blocked
    CANCELLED = "cancelled"  # User cancelled subscription

    def has_access(self) -> bool:
        """Check if this status allows product access."""
        return self in (SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE)

    def is_billable(self) -> bool:
        """Check if this status should be billed."""
        return self in (SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE)


class SubscriptionTier(str, Enum):
    """
    Subscription pricing tiers (consumer/prosumer model).

    Maps to Stripe price IDs.
    """

    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"

    def get_price_cents(self) -> int:
        """Get monthly price in cents (fallback - Stripe is source of truth)."""
        prices = {
            SubscriptionTier.FREE: 0,
            SubscriptionTier.STARTER: 2900,  # $29
            SubscriptionTier.PROFESSIONAL: 7900,  # $79
            SubscriptionTier.BUSINESS: 19900,  # $199
            SubscriptionTier.ENTERPRISE: 99900,  # $999
        }
        return prices[self]

    def get_quota_limits(self) -> dict[str, int]:
        """
        Get usage quota limits for this tier.

        Quotas:
        - cell_operations_per_month: Number of cell creates/updates
        - agentic_qa_per_month: Number of agentic QA runs
        - workflows_per_month: Number of workflow executions
        - storage_bytes_per_month: Total bytes uploaded
        - agentic_chunking_per_month: AI-enhanced document processing
        - documents_per_month: Number of document uploads
        """
        MB = 1024 * 1024
        GB = 1024 * MB

        limits = {
            SubscriptionTier.FREE: {
                "cell_operations_per_month": 100,
                "agentic_qa_per_month": 5,
                "workflows_per_month": 0,
                "storage_bytes_per_month": 100 * MB,
                "agentic_chunking_per_month": 0,
                "documents_per_month": 10,
            },
            SubscriptionTier.STARTER: {
                "cell_operations_per_month": 500,
                "agentic_qa_per_month": 25,
                "workflows_per_month": 5,
                "storage_bytes_per_month": 500 * MB,
                "agentic_chunking_per_month": 25,
                "documents_per_month": 50,
            },
            SubscriptionTier.PROFESSIONAL: {
                "cell_operations_per_month": 2_500,
                "agentic_qa_per_month": 150,
                "workflows_per_month": 25,
                "storage_bytes_per_month": 2 * GB,
                "agentic_chunking_per_month": 200,
                "documents_per_month": 250,
            },
            SubscriptionTier.BUSINESS: {
                "cell_operations_per_month": 10_000,
                "agentic_qa_per_month": 400,
                "workflows_per_month": 50,
                "storage_bytes_per_month": 10 * GB,
                "agentic_chunking_per_month": 500,
                "documents_per_month": 1_000,
            },
            SubscriptionTier.ENTERPRISE: {
                "cell_operations_per_month": 50_000,
                "agentic_qa_per_month": 2_000,
                "workflows_per_month": 200,
                "storage_bytes_per_month": 50 * GB,
                "agentic_chunking_per_month": 1_000,
                "documents_per_month": 5_000,
            },
        }
        return limits[self]


class UsageEventType(str, Enum):
    """Types of billable usage events."""

    CELL_OPERATION = "cell_operation"
    AGENTIC_QA = "agentic_qa"
    WORKFLOW = "workflow"
    STORAGE_UPLOAD = "storage_upload"
    AGENTIC_CHUNKING = "agentic_chunking"


class PaymentProvider(str, Enum):
    """Supported payment providers."""

    STRIPE = "stripe"
    MANUAL = "manual"  # For manual invoicing/wire transfers


class InvoiceStatus(str, Enum):
    """Invoice payment status."""

    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    VOID = "void"
