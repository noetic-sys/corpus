from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Header

from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.auth.providers.models import SSOProvider
from packages.auth.services.sso_auth_service import SSOAuthService
from packages.auth.services.service_account_service import ServiceAccountService
from packages.users.services.user_service import UserService
from packages.billing.services.subscription_service import SubscriptionService

logger = get_logger(__name__)


def get_sso_auth_service() -> SSOAuthService:
    """Get SSOAuthService instance."""
    return SSOAuthService(SSOProvider.FIREBASE)


@trace_span
async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
    x_api_key: Annotated[Optional[str], Header()] = None,
    sso_auth_service: SSOAuthService = Depends(get_sso_auth_service),
) -> AuthenticatedUser:
    """Get current authenticated user from SSO JWT token or API key."""
    # Try API key first
    if x_api_key:
        service_account_service = ServiceAccountService()
        user = await service_account_service.authenticate_api_key(x_api_key)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        # Verify company has active subscription
        subscription_service = SubscriptionService()
        subscription = await subscription_service.get_by_company_id(user.company_id)
        if not subscription or not subscription.has_access():
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Active subscription required for API access",
            )

        return user

    # Fall back to SSO token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]

    return await sso_auth_service.authenticate_user_from_token(token)


@trace_span
async def get_service_account(
    x_api_key: Annotated[Optional[str], Header()] = None,
) -> AuthenticatedUser:
    """Get authenticated service account (API key only, no SSO tokens)."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )

    service_account_service = ServiceAccountService()
    user = await service_account_service.authenticate_api_key(x_api_key)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return user


@trace_span
async def get_current_active_user(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Get current active user."""
    # if not current_user.is_active:
    #    raise HTTPException(status_code=400, detail="Inactive user")
    logger.info(
        f"Getting workspace for company_id={current_user.company_id} user_id={current_user.user_id}"
    )
    return current_user


@trace_span
async def get_subscribed_user(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
) -> AuthenticatedUser:
    """Get current user with active subscription check."""
    subscription_service = SubscriptionService()
    subscription = await subscription_service.get_by_company_id(current_user.company_id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="No subscription found. Please subscribe to continue.",
        )

    if not subscription.has_access():
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Subscription is {subscription.status.value}. Please update billing.",
        )

    return current_user


@trace_span
async def get_current_admin_user(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
) -> AuthenticatedUser:
    """Get current admin user."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user


@trace_span
async def get_current_active_user_from_token(token: str) -> AuthenticatedUser:
    """Get current active user directly from token."""
    sso_auth_service = get_sso_auth_service()
    user = await sso_auth_service.authenticate_user_from_token(token)

    # if not user.is_active:
    #    raise HTTPException(status_code=400, detail="Inactive user")

    return user


def get_user_service() -> UserService:
    """Get UserService instance."""
    return UserService()
