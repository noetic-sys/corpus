"""
Plans API routes.

Public endpoint for retrieving available subscription plans.
"""

from fastapi import APIRouter

from packages.billing.services.plans_service import PlansService
from packages.billing.models.domain.plans import PlansResponse

router = APIRouter()


@router.get("", response_model=PlansResponse)
async def get_plans():
    """
    Get all available subscription plans.

    Returns pricing, limits, and features for each tier.
    Prices are fetched from Stripe and cached for 1 hour.
    This endpoint is public (no auth required) for pricing pages.
    """
    plans_service = PlansService()
    return await plans_service.get_all_plans()
