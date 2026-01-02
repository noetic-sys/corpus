"""
Webhook endpoints for billing events.

Public endpoints (no auth required) for Stripe webhooks.
"""

from fastapi import APIRouter, Request

from packages.billing.webhooks.stripe_webhook import handle_stripe_webhook

router = APIRouter()


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request) -> dict[str, str]:
    """
    Receive webhook events from Stripe payment platform.

    No authentication required - webhook signature validated internally.
    """
    return await handle_stripe_webhook(request)
