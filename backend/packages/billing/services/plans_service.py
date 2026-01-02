"""Service for retrieving billing plan information."""

import stripe

from common.core.config import settings
from common.core.otel_axiom_exporter import trace_span, get_logger
from common.providers.caching.decorators import cache
from packages.billing.models.domain.enums import SubscriptionTier
from packages.billing.models.domain.plans import PlanInfo, PlanLimits, PlansResponse

logger = get_logger(__name__)

# Plan metadata that doesn't come from Stripe or the enum
PLAN_METADATA = {
    SubscriptionTier.FREE: {
        "name": "Free",
        "description": "Try it out",
    },
    SubscriptionTier.STARTER: {
        "name": "Starter",
        "description": "For individual prosumers",
    },
    SubscriptionTier.PROFESSIONAL: {
        "name": "Professional",
        "description": "For power users & small teams",
    },
    SubscriptionTier.BUSINESS: {
        "name": "Business",
        "description": "For teams & departments",
    },
    SubscriptionTier.ENTERPRISE: {
        "name": "Enterprise",
        "description": "For large organizations",
    },
}


class PlansService:
    """Service for retrieving plan information."""

    def __init__(self):
        stripe.api_key = settings.stripe_secret_key
        self._price_ids = {
            SubscriptionTier.STARTER: settings.stripe_price_id_starter,
            SubscriptionTier.PROFESSIONAL: settings.stripe_price_id_professional,
            SubscriptionTier.BUSINESS: settings.stripe_price_id_business,
            SubscriptionTier.ENTERPRISE: settings.stripe_price_id_enterprise,
        }

    @trace_span
    async def get_all_plans(self) -> PlansResponse:
        """Get all available plans with pricing and limits."""
        # Fetch Stripe prices (cached)
        stripe_prices = await self._get_stripe_prices()

        plans = []
        for tier in SubscriptionTier:
            plan_info = self._build_plan_info(tier, stripe_prices)
            plans.append(plan_info)

        return PlansResponse(plans=plans)

    def _build_plan_info(
        self, tier: SubscriptionTier, stripe_prices: dict[str, int]
    ) -> PlanInfo:
        """Build PlanInfo for a tier."""
        limits_dict = tier.get_quota_limits()
        metadata = PLAN_METADATA[tier]

        # Get price - from Stripe if available, otherwise from enum
        price_id = self._price_ids.get(tier)
        if price_id and price_id in stripe_prices:
            price_cents = stripe_prices[price_id]
        else:
            price_cents = tier.get_price_cents()

        # Format price
        price_dollars = price_cents / 100
        if price_cents == 0:
            price_formatted = "$0"
        elif price_dollars == int(price_dollars):
            price_formatted = f"${int(price_dollars)}"
        else:
            price_formatted = f"${price_dollars:.2f}"

        # Build features list from limits
        features = self._build_features_list(limits_dict)

        return PlanInfo(
            tier=tier.value,
            name=metadata["name"],
            description=metadata["description"],
            price_cents=price_cents,
            price_formatted=price_formatted,
            billing_period="month",
            stripe_price_id=price_id,
            limits=PlanLimits(
                cell_operations_per_month=limits_dict["cell_operations_per_month"],
                agentic_qa_per_month=limits_dict["agentic_qa_per_month"],
                workflows_per_month=limits_dict["workflows_per_month"],
                storage_bytes=limits_dict["storage_bytes_per_month"],
            ),
            features=features,
        )

    def _build_features_list(self, limits: dict[str, int]) -> list[str]:
        """Build human-readable features list from limits."""
        cell_ops = limits["cell_operations_per_month"]
        agentic_qa = limits["agentic_qa_per_month"]
        workflows = limits["workflows_per_month"]
        storage_bytes = limits["storage_bytes_per_month"]

        # Format storage
        if storage_bytes >= 1024 * 1024 * 1024:
            storage_str = f"{storage_bytes // (1024 * 1024 * 1024)} GB storage"
        else:
            storage_str = f"{storage_bytes // (1024 * 1024)} MB storage"

        return [
            f"{cell_ops:,} cell operations",
            f"{agentic_qa:,} agentic QA",
            f"{workflows:,} workflow{'s' if workflows != 1 else ''}",
            storage_str,
        ]

    @trace_span
    async def _get_stripe_prices(self) -> dict[str, int]:
        """
        Fetch prices from Stripe.

        Returns dict mapping price_id -> amount in cents.
        Cached for 1 hour since prices rarely change.
        """
        return await self._fetch_stripe_prices_cached()

    @cache(model_type=dict, ttl=3600, key_generator=lambda: "stripe_prices")
    async def _fetch_stripe_prices_cached(self) -> dict[str, int]:
        """Fetch and cache Stripe prices."""
        prices = {}

        for tier, price_id in self._price_ids.items():
            if not price_id:
                continue

            try:
                price = stripe.Price.retrieve(price_id)
                prices[price_id] = price.unit_amount or 0
                logger.debug(
                    f"Fetched Stripe price for {tier.value}",
                    extra={"price_id": price_id, "amount": price.unit_amount},
                )
            except stripe.error.StripeError as e:
                logger.warning(
                    f"Failed to fetch Stripe price {price_id}: {e}",
                    extra={"price_id": price_id, "error": str(e)},
                )
                # Fall back to enum price
                prices[price_id] = tier.get_price_cents()

        return prices
