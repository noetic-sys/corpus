"""
Billing API routes.

Protected endpoints for subscription and usage management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.session import get_db
from packages.auth.dependencies import get_current_active_user
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.billing.models.domain.enums import SubscriptionTier
from packages.billing.services.subscription_service import SubscriptionService
from packages.billing.services.quota_service import QuotaService
from packages.billing.models.schemas.billing import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    PortalSessionRequest,
    PortalSessionResponse,
    SubscriptionStatusResponse,
    UsageStatsResponse,
    QuotaStatusResponse,
    UpgradeTierRequest,
    UpgradeTierResponse,
    CancelSubscriptionResponse,
)

router = APIRouter()


# ============================================================================
# Subscription Status
# ============================================================================


@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Get current subscription status for the company.

    Returns subscription tier, status, and access information.
    If no subscription exists, creates a FREE tier subscription.
    """
    subscription_service = SubscriptionService(db_session)

    subscription = await subscription_service.get_by_company_id(current_user.company_id)

    # Lazy backfill: create FREE subscription if none exists
    if not subscription:
        subscription = await subscription_service.create_subscription(
            company_id=current_user.company_id,
            company_name=f"Company {current_user.company_id}",
            tier=SubscriptionTier.FREE,
        )

    return SubscriptionStatusResponse(
        company_id=subscription.company_id,
        tier=subscription.tier,
        status=subscription.status,
        has_access=subscription.has_access(),
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancelled_at=subscription.cancelled_at,
        suspended_at=subscription.suspended_at,
    )


# ============================================================================
# Usage Stats
# ============================================================================


@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Get detailed usage statistics for the company.

    Returns current usage counts, limits, and percentages for all 4 quota types.
    If no subscription exists, creates a FREE tier subscription.
    """
    subscription_service = SubscriptionService(db_session)
    quota_service = QuotaService(db_session)

    # Ensure subscription exists (lazy backfill for existing companies)
    subscription = await subscription_service.get_by_company_id(current_user.company_id)
    if not subscription:
        await subscription_service.create_subscription(
            company_id=current_user.company_id,
            company_name=f"Company {current_user.company_id}",
            tier=SubscriptionTier.FREE,
        )

    stats = await quota_service.get_usage_stats(current_user.company_id)

    # Calculate percentages
    cell_ops_pct = (
        (stats.cell_operations / stats.cell_operations_limit * 100)
        if stats.cell_operations_limit
        else 0
    )
    agentic_qa_pct = (
        (stats.agentic_qa / stats.agentic_qa_limit * 100)
        if stats.agentic_qa_limit
        else 0
    )
    workflows_pct = (
        (stats.workflows / stats.workflows_limit * 100) if stats.workflows_limit else 0
    )
    storage_pct = (
        (stats.storage_bytes / stats.storage_bytes_limit * 100)
        if stats.storage_bytes_limit
        else 0
    )
    agentic_chunking_pct = (
        (stats.agentic_chunking / stats.agentic_chunking_limit * 100)
        if stats.agentic_chunking_limit
        else 0
    )
    documents_pct = (
        (stats.documents / stats.documents_limit * 100) if stats.documents_limit else 0
    )

    return UsageStatsResponse(
        company_id=stats.company_id,
        tier=stats.tier,
        cell_operations=stats.cell_operations,
        cell_operations_limit=stats.cell_operations_limit,
        cell_operations_percentage=cell_ops_pct,
        agentic_qa=stats.agentic_qa,
        agentic_qa_limit=stats.agentic_qa_limit,
        agentic_qa_percentage=agentic_qa_pct,
        workflows=stats.workflows,
        workflows_limit=stats.workflows_limit,
        workflows_percentage=workflows_pct,
        storage_bytes=stats.storage_bytes,
        storage_bytes_limit=stats.storage_bytes_limit,
        storage_bytes_percentage=storage_pct,
        agentic_chunking=stats.agentic_chunking,
        agentic_chunking_limit=stats.agentic_chunking_limit,
        agentic_chunking_percentage=agentic_chunking_pct,
        documents=stats.documents,
        documents_limit=stats.documents_limit,
        documents_percentage=documents_pct,
        period_start=stats.period_start,
        period_end=stats.period_end,
    )


@router.get("/quota/cell-operations", response_model=QuotaStatusResponse)
async def check_cell_operation_quota(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Check current cell operation quota status.

    Returns detailed quota information for cell operations metric.
    Raises 429 if quota exceeded.
    """
    quota_service = QuotaService(db_session)

    quota_check = await quota_service.check_cell_operation_quota(
        current_user.company_id
    )

    return QuotaStatusResponse(
        metric_name=quota_check.metric_name,
        current_usage=quota_check.current_usage,
        limit=quota_check.limit,
        remaining=quota_check.remaining,
        percentage_used=quota_check.percentage_used,
        warning_threshold_reached=quota_check.warning_threshold_reached,
        period_type=quota_check.period_type,
        period_end=quota_check.period_end,
    )


# ============================================================================
# Checkout & Portal
# ============================================================================


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CheckoutSessionRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Create a Stripe checkout session or update existing subscription.

    - No subscription / FREE tier → Checkout session for new subscription
    - Paid tier → Update existing subscription (no new checkout)
    """
    subscription_service = SubscriptionService(db_session)

    # Check if subscription already exists
    existing = await subscription_service.get_by_company_id(current_user.company_id)

    company_name = (
        current_user.company.name
        if hasattr(current_user, "company")
        else f"Company {current_user.company_id}"
    )

    # FREE tier request: downgrade or create free subscription
    if request.tier == SubscriptionTier.FREE:
        if existing:
            if existing.tier == SubscriptionTier.FREE:
                # Already on FREE, nothing to do
                return CheckoutSessionResponse(checkout_url=str(request.success_url))

            # Downgrade from paid to FREE: cancel Stripe subscription
            await subscription_service.downgrade_to_free(current_user.company_id)
            return CheckoutSessionResponse(checkout_url=str(request.success_url))

        # No subscription exists, create FREE subscription
        await subscription_service.create_subscription(
            company_id=current_user.company_id,
            company_name=company_name,
            tier=request.tier,
            billing_email=request.billing_email,
        )
        return CheckoutSessionResponse(checkout_url=str(request.success_url))

    # Paid tier request with existing PAID subscription → Update in place
    if existing and existing.tier != SubscriptionTier.FREE:
        if existing.tier == request.tier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Already on {request.tier.value} tier.",
            )

        if not existing.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Stripe subscription found. Please contact support.",
            )

        # Update existing Stripe subscription (no new checkout)
        await subscription_service.update_subscription_tier(
            company_id=current_user.company_id,
            new_tier=request.tier,
        )

        # Redirect to success URL - subscription updated immediately
        return CheckoutSessionResponse(checkout_url=str(request.success_url))

    # No subscription or FREE tier → Create Stripe checkout session
    checkout_url = await subscription_service.create_checkout_session(
        company_id=current_user.company_id,
        company_name=company_name,
        tier=request.tier,
        success_url=str(request.success_url),
        cancel_url=str(request.cancel_url),
        billing_email=request.billing_email,
        trial_period_days=request.trial_period_days,
    )

    return CheckoutSessionResponse(checkout_url=checkout_url)


@router.post("/portal", response_model=PortalSessionResponse)
async def create_portal_session(
    request: PortalSessionRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Create a Stripe customer portal session.

    Allows customers to manage payment methods, view invoices, cancel subscription.
    """
    subscription_service = SubscriptionService(db_session)

    portal_url = await subscription_service.create_portal_session(
        company_id=current_user.company_id,
        return_url=str(request.return_url),
    )

    return PortalSessionResponse(portal_url=portal_url)


# ============================================================================
# Tier Management
# ============================================================================


@router.post("/upgrade", response_model=UpgradeTierResponse)
async def upgrade_tier(
    request: UpgradeTierRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Upgrade subscription tier.

    Only admin users can upgrade tiers.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company admins can upgrade subscription tier",
        )

    subscription_service = SubscriptionService(db_session)

    subscription = await subscription_service.get_by_company_id(current_user.company_id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No subscription found"
        )

    old_tier = subscription.tier

    updated = await subscription_service.upgrade_tier(
        company_id=current_user.company_id,
        new_tier=request.new_tier,
    )

    return UpgradeTierResponse(
        success=True,
        message=f"Successfully upgraded from {old_tier.value} to {request.new_tier.value}",
        new_tier=updated.tier,
        old_tier=old_tier,
    )


# ============================================================================
# Cancellation
# ============================================================================


@router.post("/cancel", response_model=CancelSubscriptionResponse)
async def cancel_subscription(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Cancel subscription.

    Only admin users can cancel subscription.
    Access continues until end of current billing period.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company admins can cancel subscription",
        )

    subscription_service = SubscriptionService(db_session)

    cancelled = await subscription_service.cancel_subscription(current_user.company_id)

    return CancelSubscriptionResponse(
        success=True,
        message="Subscription cancelled successfully. Access continues until end of billing period.",
        cancelled_at=cancelled.cancelled_at,
        access_until=cancelled.current_period_end,
    )
