"""
Domain models for Stripe webhook payloads.

Strongly-typed Pydantic models for Stripe payment platform webhook events.
"""

from typing import Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class StripeWebhookType(str, Enum):
    """Stripe webhook event types we care about."""

    # Checkout
    CHECKOUT_SESSION_COMPLETED = "checkout.session.completed"
    CHECKOUT_SESSION_EXPIRED = "checkout.session.expired"

    # Customer
    CUSTOMER_CREATED = "customer.created"
    CUSTOMER_UPDATED = "customer.updated"
    CUSTOMER_DELETED = "customer.deleted"

    # Subscription
    SUBSCRIPTION_CREATED = "customer.subscription.created"
    SUBSCRIPTION_UPDATED = "customer.subscription.updated"
    SUBSCRIPTION_DELETED = "customer.subscription.deleted"
    SUBSCRIPTION_TRIAL_WILL_END = "customer.subscription.trial_will_end"

    # Payment
    INVOICE_CREATED = "invoice.created"
    INVOICE_FINALIZED = "invoice.finalized"
    INVOICE_PAID = "invoice.paid"
    INVOICE_PAYMENT_FAILED = "invoice.payment_failed"
    INVOICE_PAYMENT_ACTION_REQUIRED = "invoice.payment_action_required"

    # Payment method
    PAYMENT_METHOD_ATTACHED = "payment_method.attached"
    PAYMENT_METHOD_DETACHED = "payment_method.detached"
    PAYMENT_METHOD_UPDATED = "payment_method.updated"


class StripeSubscriptionStatus(str, Enum):
    """Stripe subscription status values."""

    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    PAUSED = "paused"


class StripeMetadata(BaseModel):
    """Stripe metadata (we store company_id here)."""

    company_id: Optional[str] = None
    company_name: Optional[str] = None
    tier: Optional[str] = None


class StripeCustomerData(BaseModel):
    """Stripe customer object."""

    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    metadata: StripeMetadata = Field(default_factory=StripeMetadata)
    created: int


class StripeSubscriptionData(BaseModel):
    """Stripe subscription object."""

    id: str
    customer: str
    status: StripeSubscriptionStatus
    current_period_start: int
    current_period_end: int
    cancel_at_period_end: bool
    canceled_at: Optional[int] = None
    ended_at: Optional[int] = None
    trial_start: Optional[int] = None
    trial_end: Optional[int] = None
    metadata: StripeMetadata = Field(default_factory=StripeMetadata)


class StripeInvoiceData(BaseModel):
    """Stripe invoice object."""

    id: str
    customer: str
    subscription: Optional[str] = None
    status: str
    amount_due: int
    amount_paid: int
    amount_remaining: int
    currency: str
    hosted_invoice_url: Optional[str] = None
    invoice_pdf: Optional[str] = None
    paid: bool
    payment_intent: Optional[str] = None


class StripeCheckoutSessionData(BaseModel):
    """Stripe checkout session object."""

    id: str
    customer: Optional[str] = None
    subscription: Optional[str] = None
    payment_status: str
    status: str
    amount_total: Optional[int] = None
    currency: Optional[str] = None
    customer_email: Optional[str] = None
    metadata: StripeMetadata = Field(default_factory=StripeMetadata)


class StripeEventData(BaseModel):
    """Stripe event data wrapper."""

    object: dict[str, Any]  # The actual object (customer, subscription, invoice, etc.)


class StripeWebhookPayload(BaseModel):
    """Complete Stripe webhook payload."""

    id: str
    type: StripeWebhookType
    data: StripeEventData
    created: int
    livemode: bool
