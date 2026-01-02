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

    FREE = "free"  # $0/mo - lead generation
    STARTER = "starter"  # $19/mo - individual prosumers
    PROFESSIONAL = "professional"  # $49/mo - power users & small teams
    BUSINESS = "business"  # $179/mo - teams & departments
    ENTERPRISE = "enterprise"  # $499+/mo - custom/high volume

    def get_price_cents(self) -> int:
        """Get monthly price in cents."""
        prices = {
            SubscriptionTier.FREE: 0,
            SubscriptionTier.STARTER: 1900,  # $19
            SubscriptionTier.PROFESSIONAL: 4900,  # $49
            SubscriptionTier.BUSINESS: 17900,  # $179
            SubscriptionTier.ENTERPRISE: 49900,  # $499 base
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
                "workflows_per_month": 1,
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
                "cell_operations_per_month": 100_000,
                "agentic_qa_per_month": 5_000,
                "workflows_per_month": 500,
                "storage_bytes_per_month": 50 * GB,
                "agentic_chunking_per_month": 999_999,  # Effectively unlimited
                "documents_per_month": 10_000,
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
