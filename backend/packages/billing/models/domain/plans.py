"""Domain models for billing plans."""

from typing import Optional
from pydantic import BaseModel


class PlanLimits(BaseModel):
    """Quota limits for a plan."""

    cell_operations_per_month: int
    agentic_qa_per_month: int
    workflows_per_month: int
    storage_bytes: int


class PlanInfo(BaseModel):
    """Complete plan information combining pricing and limits."""

    tier: str
    name: str
    description: str
    price_cents: int
    price_formatted: str
    billing_period: str
    stripe_price_id: Optional[str]
    limits: PlanLimits
    features: list[str]


class PlansResponse(BaseModel):
    """Response model for plans endpoint."""

    plans: list[PlanInfo]
