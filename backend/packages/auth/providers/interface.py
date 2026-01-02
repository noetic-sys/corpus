from abc import ABC, abstractmethod

from packages.auth.providers.models import SSOUserInfo, SSOProvider


class SSOProviderInterface(ABC):
    """Interface for SSO providers"""

    @abstractmethod
    async def validate_token(self, token: str) -> bool:
        """Validate the SSO token"""
        pass

    @abstractmethod
    async def get_user_info(self, token: str) -> SSOUserInfo:
        """Extract user information from validated token"""
        pass

    @abstractmethod
    def get_provider_name(self) -> SSOProvider:
        """Get the provider name"""
        pass

    @abstractmethod
    async def get_provider_user_id_from_token(self, token: str) -> str:
        """Extract provider user ID from token without external API calls"""
        pass
