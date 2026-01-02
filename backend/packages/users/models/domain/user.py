from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class User(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    company_id: int
    is_active: bool = True
    is_admin: bool = False
    sso_provider: Optional[str] = None
    sso_user_id: Optional[str] = None
    deleted: bool = False
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreateModel(BaseModel):
    """Model for creating a new user."""

    email: EmailStr
    full_name: Optional[str] = None
    company_id: int
    is_active: bool = True
    is_admin: bool = False
    sso_provider: Optional[str] = None
    sso_user_id: Optional[str] = None


class UserUpdateModel(BaseModel):
    """Model for updating a user."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    sso_provider: Optional[str] = None
    sso_user_id: Optional[str] = None
