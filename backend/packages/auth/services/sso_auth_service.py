from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from packages.auth.providers.models import SSOProvider
from packages.auth.providers.factory import get_sso_provider
from packages.users.services.user_service import UserService
from packages.companies.services.company_service import CompanyService
from packages.billing.services.subscription_service import SubscriptionService
from packages.billing.models.domain.enums import SubscriptionTier
from packages.billing.providers.payment.factory import get_payment_provider
from packages.users.models.domain.user import User, UserCreateModel
from packages.companies.models.domain.company import (
    CompanyCreateModel,
    CompanyUpdateModel,
)
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from common.core.otel_axiom_exporter import trace_span, get_logger
from common.providers.bloom_filter.factory import get_bloom_filter_provider


logger = get_logger(__name__)


class SSOAuthService:
    """Unified service for handling SSO authentication with any provider"""

    def __init__(self, db_session: AsyncSession, provider: SSOProvider):
        self.db_session = db_session
        self.user_service = UserService(db_session)
        self.company_service = CompanyService(db_session)
        self.subscription_service = SubscriptionService(db_session)
        self.bloom_filter = get_bloom_filter_provider()

        # Get singleton provider instance from factory
        self.sso_provider = get_sso_provider(provider)

    @trace_span
    async def authenticate_user_from_token(self, token: str) -> AuthenticatedUser:
        """Authenticate user from SSO JWT token with optimized local lookup"""

        # Validate token and get basic claims (no external API call)
        is_valid = await self.sso_provider.validate_token(token)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid {self.sso_provider.get_provider_name().value} token",
            )

        # Get provider user ID from token claims (no external API call)
        provider_user_id = await self.sso_provider.get_provider_user_id_from_token(
            token
        )
        provider_name = self.sso_provider.get_provider_name().value

        # Fast bloom filter check
        bloom_key = f"{provider_name}:{provider_user_id}"
        might_exist = await self.bloom_filter.exists("sso_users", bloom_key)

        user = None
        if might_exist:
            # Check database for existing user
            user = await self.user_service.get_by_sso(provider_name, provider_user_id)

        if user:
            # Existing user found, no need for external API calls
            # await self.user_service.update_last_login(user.id)
            logger.info("Found user")
            return AuthenticatedUser(company_id=user.company_id, user_id=user.id)

        logger.info("Creating new user")
        # New user - need to fetch full profile info from SSO provider
        sso_user_info = await self.sso_provider.get_user_info(token)

        # Create new user
        user = await self._create_new_user(sso_user_info)

        # Add to bloom filter for future fast lookups
        await self.bloom_filter.add("sso_users", bloom_key)

        # Update last login and return
        # await self.user_service.update_last_login(user.id)

        return AuthenticatedUser(company_id=user.company_id, user_id=user.id)

    @trace_span
    async def _create_new_user(self, sso_user_info) -> User:
        """Create new user from SSO info (simplified since we know user doesn't exist)"""

        provider_name = self.sso_provider.get_provider_name().value

        # Get or create company first
        company = await self._get_or_create_company_for_email(sso_user_info.email)

        # Create user
        user_data = UserCreateModel(
            email=sso_user_info.email,
            full_name=sso_user_info.full_name,
            company_id=company.id,
            sso_provider=provider_name,
            sso_user_id=sso_user_info.provider_user_id,
            is_admin=self._determine_admin_status(sso_user_info),
        )

        return await self.user_service.create_sso_user(user_data)

    @trace_span
    async def _get_or_create_company_for_email(self, email: str):
        """Get or create company based on email domain"""

        # Extract domain from email
        domain = email.split("@")[1].lower()

        # Handle generic email providers - create personal company
        generic_domains = [
            "gmail.com",
            "yahoo.com",
            "hotmail.com",
            "outlook.com",
            "icloud.com",
        ]
        if domain in generic_domains:
            # Check if user with this email already exists (prevents duplicates on race conditions)
            existing_user = await self.user_service.get_by_email(email)
            if existing_user:
                logger.info(
                    f"Found existing user for personal email {email}, returning their company"
                )
                return await self.company_service.get_company(existing_user.company_id)

            company_name = f"{email.split('@')[0].title()} Personal"
            company_data = CompanyCreateModel(
                name=company_name,
                domain=None,  # No domain for personal accounts
                description=f"Personal account for {email}",
            )
            company = await self.company_service.create_personal_company(company_data)
            await self._create_free_subscription(company.id, company.name, email)
            return company

        # Try to find existing company by domain
        existing_company = await self.company_service.get_by_domain(domain)
        if existing_company:
            return existing_company

        # Create new company for business domain
        company_name = f"{domain.split('.')[0].title()} Organization"
        company_data = CompanyCreateModel(
            name=company_name,
            domain=domain,
            description=f"Auto-created company for {domain} domain",
        )

        company = await self.company_service.create_company(company_data)
        await self._create_free_subscription(company.id, company.name, email)
        return company

    @trace_span
    async def _create_free_subscription(
        self, company_id: int, company_name: str, billing_email: str
    ) -> None:
        """Create a Stripe customer and FREE tier subscription for a new company."""
        try:
            # Check if company already has a Stripe customer (race condition protection)
            company = await self.company_service.get_company(company_id)
            if company and company.stripe_customer_id:
                logger.info(
                    f"Company {company_id} already has Stripe customer {company.stripe_customer_id}, skipping creation"
                )
                return

            # Check if subscription already exists (race condition protection)
            existing_subscription = await self.subscription_service.get_by_company_id(
                company_id
            )
            if existing_subscription:
                logger.info(
                    f"Company {company_id} already has subscription, skipping creation"
                )
                return

            # Create Stripe customer first (so they can access portal later)
            payment_provider = get_payment_provider()
            stripe_customer_id = await payment_provider.create_customer(
                company_id=company_id,
                company_name=company_name,
                email=billing_email,
            )

            # Save Stripe customer ID on company
            await self.company_service.update_company(
                company_id,
                CompanyUpdateModel(stripe_customer_id=stripe_customer_id),
            )

            # Create FREE subscription in our database
            await self.subscription_service.create_subscription(
                company_id=company_id,
                company_name=company_name,
                tier=SubscriptionTier.FREE,
                billing_email=billing_email,
            )

            logger.info(
                "Created Stripe customer and FREE subscription for new company",
                extra={
                    "company_id": company_id,
                    "company_name": company_name,
                    "stripe_customer_id": stripe_customer_id,
                },
            )
        except Exception as e:
            # Log but don't fail user signup if subscription creation fails
            logger.error(
                f"Failed to create FREE subscription for company {company_id}: {e}",
                extra={"company_id": company_id, "error": str(e)},
            )

    def _determine_admin_status(self, sso_user_info) -> bool:
        """Determine if user should be admin based on SSO groups or other criteria"""
        # Check for admin groups - customize this based on your SSO group setup
        admin_groups = ["Corpus_Admins", "Administrators", "Admin"]

        # For Auth0, groups might be empty by default
        if not sso_user_info.groups:
            return False

        return any(group in sso_user_info.groups for group in admin_groups)
