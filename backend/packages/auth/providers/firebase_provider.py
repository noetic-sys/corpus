"""Firebase Auth provider implementation."""

from typing import Optional

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from fastapi import HTTPException, status
from opentelemetry import trace

from common.core.otel_axiom_exporter import trace_span, get_logger
from common.core.config import settings
from packages.auth.providers.interface import SSOProviderInterface
from packages.auth.providers.models import SSOUserInfo, SSOProvider

tracer = trace.get_tracer(__name__)
logger = get_logger(__name__)

# Firebase Admin SDK initialization (uses Workload Identity automatically on GKE)
_firebase_app: Optional[firebase_admin.App] = None


def _get_firebase_app() -> firebase_admin.App:
    """Get or initialize Firebase Admin app."""
    global _firebase_app
    if _firebase_app is None:
        project_id = settings.firebase_project_id or settings.google_project_id
        if not project_id:
            raise ValueError(
                "Firebase configuration missing: firebase_project_id or google_project_id required"
            )

        # Load credentials explicitly if path is provided (local dev)
        # On GKE with Workload Identity, this will be None and ADC is used
        cred = None
        if settings.google_application_credentials:
            cred = credentials.Certificate(settings.google_application_credentials)

        _firebase_app = firebase_admin.initialize_app(
            credential=cred, options={"projectId": project_id}
        )
        logger.info(f"Firebase Admin SDK initialized for project: {project_id}")
    return _firebase_app


class FirebaseAuthProvider(SSOProviderInterface):
    """Firebase Auth provider implementation."""

    def __init__(self):
        """Initialize Firebase provider."""
        self.app = _get_firebase_app()

    @trace_span
    async def validate_token(self, token: str) -> bool:
        """Validate a Firebase ID token."""
        try:
            firebase_auth.verify_id_token(token, app=self.app)
            return True
        except Exception as e:
            logger.warning(f"Firebase token validation failed: {e}")
            return False

    @trace_span
    async def get_user_info(self, token: str) -> SSOUserInfo:
        """Get user info from Firebase ID token."""
        try:
            # Verify token and get claims
            decoded_token = firebase_auth.verify_id_token(token, app=self.app)
            uid = decoded_token["uid"]

            # Get full user record for additional details
            user_record = firebase_auth.get_user(uid, app=self.app)

            # Extract email (required)
            email = user_record.email
            if not email:
                raise ValueError("Email not found in Firebase user record")

            # Build name from display_name
            full_name = user_record.display_name
            if not full_name:
                # Use email prefix as fallback
                full_name = email.split("@")[0]

            return SSOUserInfo(
                email=email,
                full_name=full_name,
                first_name=None,  # Firebase doesn't split names
                last_name=None,
                groups=[],  # Firebase doesn't have built-in groups
                is_active=not user_record.disabled,
                provider_user_id=uid,
            )

        except firebase_auth.InvalidIdTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Firebase token: {str(e)}",
            )
        except firebase_auth.ExpiredIdTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firebase token has expired",
            )
        except firebase_auth.UserNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firebase user not found",
            )
        except Exception as e:
            logger.error(f"Failed to get Firebase user info: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to extract user info from Firebase token: {str(e)}",
            )

    def get_provider_name(self) -> SSOProvider:
        """Return provider identifier."""
        return SSOProvider.FIREBASE

    @trace_span
    async def get_provider_user_id_from_token(self, token: str) -> str:
        """Extract Firebase UID from token."""
        try:
            decoded_token = firebase_auth.verify_id_token(token, app=self.app)
            uid = decoded_token.get("uid")
            if not uid:
                raise ValueError("Token missing 'uid' claim")
            return uid
        except firebase_auth.InvalidIdTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Firebase token: {str(e)}",
            )
        except firebase_auth.ExpiredIdTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firebase token has expired",
            )
        except Exception as e:
            logger.warning(f"Failed to extract Firebase UID: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to extract user ID from Firebase token: {str(e)}",
            )
