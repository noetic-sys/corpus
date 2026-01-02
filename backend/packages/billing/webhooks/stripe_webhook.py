"""
Stripe webhook handler for payment events.

Handles events from Stripe payment platform:
- Checkout session completion
- Subscription lifecycle events
- Payment success/failure
- Customer updates
"""

import stripe
from fastapi import Request, HTTPException, status
from pydantic import ValidationError
from datetime import datetime

from common.core.config import settings
from common.core.otel_axiom_exporter import get_logger
from common.db.session import get_db
from common.providers.caching.factory import get_cache_provider
from packages.billing.cache_keys import subscription_by_company_key
from packages.billing.services.subscription_service import SubscriptionService
from packages.billing.models.domain.enums import SubscriptionStatus, SubscriptionTier
from packages.billing.models.domain.subscription import SubscriptionUpdateModel
from packages.billing.models.domain.stripe_webhooks import (
    StripeWebhookPayload,
    StripeWebhookType,
    StripeCheckoutSessionData,
    StripeSubscriptionData,
    StripeSubscriptionStatus,
    StripeInvoiceData,
    StripeCustomerData,
)
from packages.companies.services.company_service import CompanyService
from packages.companies.models.domain.company import CompanyUpdateModel

logger = get_logger(__name__)


async def handle_stripe_webhook(request: Request) -> dict[str, str]:
    """
    Handle incoming webhook from Stripe.

    Validates webhook signature and routes to appropriate handler.
    """
    try:
        # Get raw body for signature verification
        payload_bytes = await request.body()
        sig_header = request.headers.get("stripe-signature")

        if not sig_header:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe-signature header",
            )

        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload_bytes, sig_header, settings.stripe_webhook_secret
            )
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Stripe webhook signature verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature"
            )

        # Parse into typed model
        payload = StripeWebhookPayload(**event)

        logger.info(
            f"Received Stripe webhook: {payload.type.value}",
            extra={
                "event_id": payload.id,
                "event_type": payload.type.value,
                "livemode": payload.livemode,
            },
        )

        # Route to appropriate handler
        if payload.type == StripeWebhookType.CHECKOUT_SESSION_COMPLETED:
            await _handle_checkout_completed(payload.data.object)
        elif payload.type == StripeWebhookType.SUBSCRIPTION_CREATED:
            await _handle_subscription_created(payload.data.object)
        elif payload.type == StripeWebhookType.SUBSCRIPTION_UPDATED:
            await _handle_subscription_updated(payload.data.object)
        elif payload.type == StripeWebhookType.SUBSCRIPTION_DELETED:
            await _handle_subscription_deleted(payload.data.object)
        elif payload.type == StripeWebhookType.INVOICE_PAID:
            await _handle_invoice_paid(payload.data.object)
        elif payload.type == StripeWebhookType.INVOICE_PAYMENT_FAILED:
            await _handle_invoice_payment_failed(payload.data.object)
        elif payload.type == StripeWebhookType.CUSTOMER_UPDATED:
            await _handle_customer_updated(payload.data.object)
        else:
            logger.info(f"Unhandled Stripe webhook type: {payload.type.value}")

        return {"status": "success"}

    except ValidationError as e:
        logger.error(
            "Invalid Stripe webhook payload", extra={"validation_errors": e.errors()}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to process Stripe webhook: {str(e)}", extra={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed",
        )


async def _handle_checkout_completed(data: dict) -> None:
    """
    Handle checkout.session.completed event.

    This creates the subscription in our database after payment is confirmed.
    For paid tiers, the subscription is NOT created in the checkout route -
    it's created here after Stripe confirms payment.
    """
    try:
        session = StripeCheckoutSessionData(**data)

        company_id_str = session.metadata.company_id
        if not company_id_str:
            logger.error("Missing company_id in checkout session metadata")
            return

        company_id = int(company_id_str)
        tier_str = session.metadata.tier

        if not tier_str:
            logger.error("Missing tier in checkout session metadata")
            return

        tier = SubscriptionTier(tier_str)

        logger.info(
            f"Checkout completed for company {company_id}",
            extra={
                "company_id": company_id,
                "tier": tier.value,
                "session_id": session.id,
                "customer_id": session.customer,
                "subscription_id": session.subscription,
            },
        )

        if not session.customer or not session.subscription:
            logger.error("Missing customer or subscription ID in checkout session")
            return

        async for db_session in get_db():
            subscription_service = SubscriptionService(db_session)
            company_service = CompanyService(db_session)

            # Save stripe_customer_id on company (if not already set)
            company = await company_service.get_company(company_id)
            if company and not company.stripe_customer_id:
                await company_service.update_company(
                    company_id, CompanyUpdateModel(stripe_customer_id=session.customer)
                )

            # Check if subscription already exists (e.g., from a retry or race condition)
            existing = await subscription_service.get_by_company_id(company_id)

            if existing:
                # Update existing subscription with Stripe subscription ID and new tier
                update_data = SubscriptionUpdateModel(
                    stripe_subscription_id=session.subscription,
                    status=SubscriptionStatus.ACTIVE,
                    tier=tier,
                )
                await subscription_service.subscription_repo.update(
                    existing.id, update_data
                )

                # Invalidate subscription cache for this specific company
                cache_key = subscription_by_company_key(company_id)
                await get_cache_provider().delete(cache_key)

                logger.info(
                    f"Updated existing subscription {existing.id} with Stripe IDs and tier {tier.value}"
                )
            else:
                # Create new subscription - payment is now confirmed
                company_name = session.metadata.company_name or f"Company {company_id}"
                await subscription_service.create_subscription(
                    company_id=company_id,
                    company_name=company_name,
                    tier=tier,
                    billing_email=session.customer_email,
                )

                # Update with Stripe subscription ID
                new_sub = await subscription_service.get_by_company_id(company_id)
                if new_sub:
                    update_data = SubscriptionUpdateModel(
                        stripe_subscription_id=session.subscription,
                    )
                    await subscription_service.subscription_repo.update(
                        new_sub.id, update_data
                    )

                    # Invalidate subscription cache for this company
                    cache_key = subscription_by_company_key(company_id)
                    await get_cache_provider().delete(cache_key)

                logger.info(
                    f"Created new subscription for company {company_id} after checkout"
                )

            # Commit before breaking - break bypasses the generator's commit
            await db_session.commit()
            break

    except Exception as e:
        logger.error(
            f"Error handling checkout.session.completed: {str(e)}",
            extra={"error": str(e)},
        )


async def _handle_subscription_created(data: dict) -> None:
    """Handle customer.subscription.created event."""
    try:
        subscription = StripeSubscriptionData(**data)

        logger.info(
            f"Stripe subscription created: {subscription.id}",
            extra={
                "subscription_id": subscription.id,
                "customer_id": subscription.customer,
                "status": subscription.status.value,
            },
        )

        # Subscription is already tracked via checkout.session.completed
        # This is mainly for logging

    except Exception as e:
        logger.error(
            f"Error handling customer.subscription.created: {str(e)}",
            extra={"error": str(e)},
        )


async def _handle_subscription_updated(data: dict) -> None:
    """Handle customer.subscription.updated event."""
    try:
        subscription = StripeSubscriptionData(**data)

        company_id_str = subscription.metadata.company_id
        if not company_id_str:
            logger.warning("Missing company_id in subscription metadata")
            return

        company_id = int(company_id_str)

        # Map Stripe status to our status
        new_status = _map_stripe_status(subscription.status)

        logger.info(
            f"Stripe subscription updated: {subscription.id}",
            extra={
                "subscription_id": subscription.id,
                "company_id": company_id,
                "stripe_status": subscription.status.value,
                "our_status": new_status.value,
            },
        )

        # Update subscription status
        async for db_session in get_db():
            subscription_service = SubscriptionService(db_session)

            existing = await subscription_service.get_by_company_id(company_id)
            if existing:
                update_data = SubscriptionUpdateModel(
                    status=new_status,
                    current_period_start=datetime.fromtimestamp(
                        subscription.current_period_start
                    ),
                    current_period_end=datetime.fromtimestamp(
                        subscription.current_period_end
                    ),
                )

                if subscription.canceled_at:
                    update_data.cancelled_at = datetime.fromtimestamp(
                        subscription.canceled_at
                    )

                await subscription_service.subscription_repo.update(
                    existing.id, update_data
                )

                # Invalidate subscription cache for this company
                cache_key = subscription_by_company_key(company_id)
                await get_cache_provider().delete(cache_key)

            await db_session.commit()
            break

    except Exception as e:
        logger.error(
            f"Error handling customer.subscription.updated: {str(e)}",
            extra={"error": str(e)},
        )


async def _handle_subscription_deleted(data: dict) -> None:
    """Handle customer.subscription.deleted event."""
    try:
        subscription = StripeSubscriptionData(**data)

        company_id_str = subscription.metadata.company_id
        if not company_id_str:
            logger.warning("Missing company_id in subscription metadata")
            return

        company_id = int(company_id_str)

        logger.info(
            f"Stripe subscription deleted: {subscription.id}",
            extra={"subscription_id": subscription.id, "company_id": company_id},
        )

        # Mark subscription as cancelled
        async for db_session in get_db():
            subscription_service = SubscriptionService(db_session)
            await subscription_service.update_status(
                company_id=company_id, new_status=SubscriptionStatus.CANCELLED
            )
            break

    except Exception as e:
        logger.error(
            f"Error handling customer.subscription.deleted: {str(e)}",
            extra={"error": str(e)},
        )


async def _handle_invoice_paid(data: dict) -> None:
    """Handle invoice.paid event."""
    try:
        invoice = StripeInvoiceData(**data)

        logger.info(
            f"Stripe invoice paid: {invoice.id}",
            extra={
                "invoice_id": invoice.id,
                "customer_id": invoice.customer,
                "amount_paid": invoice.amount_paid,
                "subscription_id": invoice.subscription,
            },
        )

        # If subscription was past_due, mark as active
        if invoice.subscription:
            # Get company_id from subscription metadata
            stripe_sub = stripe.Subscription.retrieve(invoice.subscription)
            company_id_str = stripe_sub.metadata.get("company_id")

            if company_id_str:
                company_id = int(company_id_str)

                async for db_session in get_db():
                    subscription_service = SubscriptionService(db_session)

                    existing = await subscription_service.get_by_company_id(company_id)
                    if existing and existing.status == SubscriptionStatus.PAST_DUE:
                        await subscription_service.update_status(
                            company_id=company_id, new_status=SubscriptionStatus.ACTIVE
                        )
                        logger.info(
                            f"Reactivated subscription for company {company_id} after payment"
                        )

                    break

    except Exception as e:
        logger.error(f"Error handling invoice.paid: {str(e)}", extra={"error": str(e)})


async def _handle_invoice_payment_failed(data: dict) -> None:
    """Handle invoice.payment_failed event."""
    try:
        invoice = StripeInvoiceData(**data)

        logger.warning(
            f"Stripe invoice payment failed: {invoice.id}",
            extra={
                "invoice_id": invoice.id,
                "customer_id": invoice.customer,
                "amount_due": invoice.amount_due,
                "subscription_id": invoice.subscription,
            },
        )

        # Mark subscription as past_due (grace period)
        if invoice.subscription:
            stripe_sub = stripe.Subscription.retrieve(invoice.subscription)
            company_id_str = stripe_sub.metadata.get("company_id")

            if company_id_str:
                company_id = int(company_id_str)

                async for db_session in get_db():
                    subscription_service = SubscriptionService(db_session)
                    await subscription_service.update_status(
                        company_id=company_id, new_status=SubscriptionStatus.PAST_DUE
                    )
                    logger.info(
                        f"Marked subscription as past_due for company {company_id}"
                    )
                    break

        # Could send payment failure notification email here

    except Exception as e:
        logger.error(
            f"Error handling invoice.payment_failed: {str(e)}", extra={"error": str(e)}
        )


async def _handle_customer_updated(data: dict) -> None:
    """Handle customer.updated event."""
    try:
        customer = StripeCustomerData(**data)

        logger.info(
            f"Stripe customer updated: {customer.id}",
            extra={"customer_id": customer.id, "email": customer.email},
        )

        # Could sync customer data if needed

    except Exception as e:
        logger.error(
            f"Error handling customer.updated: {str(e)}", extra={"error": str(e)}
        )


def _map_stripe_status(stripe_status: StripeSubscriptionStatus) -> SubscriptionStatus:
    """Map Stripe subscription status to our subscription status."""
    mapping = {
        StripeSubscriptionStatus.ACTIVE: SubscriptionStatus.ACTIVE,
        StripeSubscriptionStatus.TRIALING: SubscriptionStatus.ACTIVE,
        StripeSubscriptionStatus.PAST_DUE: SubscriptionStatus.PAST_DUE,
        StripeSubscriptionStatus.CANCELED: SubscriptionStatus.CANCELLED,
        StripeSubscriptionStatus.UNPAID: SubscriptionStatus.SUSPENDED,
        StripeSubscriptionStatus.INCOMPLETE: SubscriptionStatus.SUSPENDED,
        StripeSubscriptionStatus.INCOMPLETE_EXPIRED: SubscriptionStatus.CANCELLED,
        StripeSubscriptionStatus.PAUSED: SubscriptionStatus.SUSPENDED,
    }
    return mapping.get(stripe_status, SubscriptionStatus.SUSPENDED)
