import json
import jwt
from jwt.algorithms import RSAAlgorithm
import httpx
import requests
from typing import Dict, Any
from functools import lru_cache
from fastapi import HTTPException, status
from opentelemetry import trace

from common.core.otel_axiom_exporter import trace_span, get_logger
from common.core.config import settings
from packages.auth.providers.interface import SSOProviderInterface
from packages.auth.providers.models import SSOUserInfo, SSOProvider

tracer = trace.get_tracer(__name__)
logger = get_logger(__name__)


class Auth0Provider(SSOProviderInterface):
    """Auth0 SSO provider implementation"""

    def __init__(self):
        """Initialize Auth0 provider with settings configuration"""
        if not all(
            [settings.auth0_domain, settings.auth0_client_id, settings.auth0_audience]
        ):
            raise ValueError(
                "Auth0 configuration missing: auth0_domain, auth0_client_id, and auth0_audience required in settings"
            )

        self.domain = settings.auth0_domain
        self.client_id = settings.auth0_client_id
        self.audience = settings.auth0_audience
        self.issuer = f"https://{self.domain}/"
        self.jwks_uri = f"https://{self.domain}/.well-known/jwks.json"

    @trace_span
    async def validate_token(self, token: str) -> bool:
        """Validate Auth0 JWT token"""
        try:
            await self._verify_token(token)
            return True
        except Exception as e:
            print(f"Token validation error: {e}")
            return False

    @trace_span
    async def get_user_info(self, token: str) -> SSOUserInfo:
        """Extract user information from Auth0 token"""
        try:
            # First verify the token is valid
            claims = await self._verify_token(token)

            # Always fetch complete user info from Auth0 userinfo endpoint
            # The access token often doesn't contain profile information
            user_info = await self._get_user_info_from_auth0_api(token)

            # Extract email (required)
            email = user_info.get("email")
            if not email:
                raise ValueError("Email not found in user info")

            # Build full name from available fields
            full_name = user_info.get("name")
            given_name = user_info.get("given_name")
            family_name = user_info.get("family_name")

            if not full_name and given_name and family_name:
                full_name = f"{given_name} {family_name}"
            elif not full_name:
                # Use email prefix as fallback
                full_name = email.split("@")[0]

            return SSOUserInfo(
                email=email,
                full_name=full_name,
                first_name=given_name,
                last_name=family_name,
                groups=[],  # Auth0 roles/permissions would be in different claim
                is_active=True,
                provider_user_id=claims.get("sub"),  # Use sub from the verified token
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to extract user info from Auth0 token: {str(e)}",
            )

    def get_provider_name(self) -> SSOProvider:
        """Get provider name"""
        return SSOProvider.AUTH0

    @trace_span
    async def get_provider_user_id_from_token(self, token: str) -> str:
        """Extract provider user ID (sub) from token without external API calls"""
        try:
            # Verify token and get claims
            claims = await self._verify_token(token)

            # Extract sub (provider user ID) from token
            provider_user_id = claims.get("sub")
            if not provider_user_id:
                raise ValueError("Token missing 'sub' claim")

            return provider_user_id

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to extract user ID from Auth0 token: {str(e)}",
            )

    @trace_span
    async def _verify_token(self, token: str) -> Dict[str, Any]:
        """Verify Auth0 JWT token signature and claims"""
        try:
            # Decode header to get the key id
            unverified_header = jwt.get_unverified_header(token)
            print(f"Token header: {unverified_header}")

            kid = unverified_header.get("kid")
            if not kid:
                raise ValueError("Token header missing 'kid'")

            # Get signing key
            signing_key = await self._get_signing_key(kid)

            # Verify token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require_exp": True,
                    "require_iat": True,
                    "require_nbf": False,
                },
            )

            print(f"Token payload: {payload}")
            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Auth0 token: {str(e)}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}",
            )

    @trace_span
    async def _get_user_info_from_auth0_api(self, token: str) -> Dict[str, Any]:
        """Get user info from Auth0 userinfo endpoint"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://{self.domain}/userinfo",
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                user_info = response.json()
                print(f"Userinfo response: {user_info}")

                return user_info

        except httpx.HTTPStatusError as e:
            error_detail = (
                f"Auth0 userinfo call failed with status {e.response.status_code}"
            )
            if e.response.text:
                error_detail += f": {e.response.text}"
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=error_detail
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to get user info from Auth0: {str(e)}",
            )

    @trace_span
    @lru_cache(maxsize=1)
    # TODO: should redis cache eventually
    def _get_jwks_sync(self) -> Dict[str, Any]:
        """Synchronously fetch JWKS - cached by functools.cache"""
        try:
            with tracer.start_as_current_span("jwks_web_request") as span:
                print(self.jwks_uri)
                response = requests.get(self.jwks_uri)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            raise ValueError(f"Failed to fetch JWKS: {str(e)}")

    @trace_span
    async def _get_signing_key(self, kid: str):
        """Get signing key from Auth0 JWKS endpoint with caching"""
        try:
            # Get cached JWKS
            jwks = self._get_jwks_sync()

            # Find key with matching kid
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    # RSAAlgorithm.from_jwk returns the key directly
                    return RSAAlgorithm.from_jwk(json.dumps(key))

            raise ValueError(f"Unable to find appropriate key for kid: {kid}")

        except Exception as e:
            raise ValueError(f"Error getting signing key: {str(e)}")
