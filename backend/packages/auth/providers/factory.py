"""Factory for creating singleton SSO provider instances."""

from typing import Dict, Optional
from packages.auth.providers.interface import SSOProviderInterface
from packages.auth.providers.models import SSOProvider
from packages.auth.providers.auth0_provider import Auth0Provider
from packages.auth.providers.firebase_provider import FirebaseAuthProvider


class SSOProviderFactory:
    """Factory for creating and managing SSO provider singletons."""

    _instances: Dict[SSOProvider, SSOProviderInterface] = {}

    @classmethod
    def get_provider(cls, provider: SSOProvider) -> SSOProviderInterface:
        """Get or create a singleton instance of the specified SSO provider.

        Args:
            provider: The SSO provider type to get

        Returns:
            SSO provider instance

        Raises:
            ValueError: If the provider is not supported
        """
        if provider not in cls._instances:
            cls._instances[provider] = cls._create_provider(provider)

        return cls._instances[provider]

    @classmethod
    def _create_provider(cls, provider: SSOProvider) -> SSOProviderInterface:
        """Create a new instance of the specified provider.

        Args:
            provider: The SSO provider type to create

        Returns:
            New SSO provider instance

        Raises:
            ValueError: If the provider is not supported
        """
        if provider == SSOProvider.FIREBASE:
            return FirebaseAuthProvider()
        elif provider == SSOProvider.AUTH0:
            return Auth0Provider()
        else:
            raise ValueError(
                f"Unsupported SSO provider: {provider}. Supported: FIREBASE, AUTH0."
            )

    @classmethod
    def clear_cache(cls, provider: Optional[SSOProvider] = None):
        """Clear cached provider instances.

        Args:
            provider: Specific provider to clear, or None to clear all
        """
        if provider:
            cls._instances.pop(provider, None)
        else:
            cls._instances.clear()


def get_sso_provider(provider: SSOProvider) -> SSOProviderInterface:
    """Convenience function to get an SSO provider instance.

    Args:
        provider: The SSO provider type to get

    Returns:
        SSO provider instance
    """
    return SSOProviderFactory.get_provider(provider)
