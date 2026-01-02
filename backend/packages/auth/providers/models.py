from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, EmailStr


class SSOProvider(str, Enum):
    """Supported SSO providers"""

    OKTA = "okta"
    AUTH0 = "auth0"
    FIREBASE = "firebase"


class SSOUserInfo(BaseModel):
    """Standardized user info from SSO providers"""

    email: EmailStr
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    groups: List[str] = []
    is_active: bool = True
    provider_user_id: str  # Provider's unique user ID


class Auth0UserClaims(BaseModel):
    """Auth0 JWT token claims"""

    sub: str  # Subject (user ID)
    email: EmailStr
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    nickname: Optional[str] = None
    picture: Optional[str] = None
    iss: str  # Issuer
    aud: str  # Audience
    exp: int  # Expiration time
    iat: int  # Issued at time


class SSOConfig(BaseModel):
    """SSO provider configuration"""

    issuer: str
    client_id: str
    audience: str
