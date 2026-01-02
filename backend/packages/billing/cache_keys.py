"""Cache key generators for billing package."""


def subscription_by_company_key(company_id: int) -> str:
    """Generate cache key for subscription by company ID."""
    return f"company:{company_id}:subscription"
