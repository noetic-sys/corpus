from pydantic import BaseModel, EmailStr
from typing import Optional


class ProtectedResponse(BaseModel):
    """Response for protected route"""

    message: str
    user_id: int
    email: EmailStr
    company_id: int
    is_admin: bool


class ProfileResponse(BaseModel):
    """User profile response"""

    id: int
    email: EmailStr
    full_name: Optional[str] = None
    company_id: int
    is_active: bool
    is_admin: bool
