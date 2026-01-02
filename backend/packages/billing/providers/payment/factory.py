"""
Factory for getting payment provider instance.
"""

from packages.billing.providers.payment.interface import PaymentProviderInterface
from packages.billing.providers.payment.stripe_payment import StripePaymentProvider


def get_payment_provider() -> PaymentProviderInterface:
    """
    Get payment provider instance based on configuration.

    Currently only Stripe is supported, but this abstraction allows
    swapping to PayPal, Paddle, etc. in the future.

    Returns:
        PaymentProviderInterface: Configured payment provider
    """
    # For now, hardcode to Stripe
    # In future, could read from settings.payment_provider
    return StripePaymentProvider()
