from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ServiceAccount(BaseModel):
    """Domain model for service accounts"""

    id: int
    name: str
    description: Optional[str] = None
    company_id: int
    api_key_hash: str
    is_active: bool = True
    deleted: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServiceAccountCreate(BaseModel):
    """Public input for creating a service account (API/callers)"""

    name: str
    description: Optional[str] = None
    company_id: int


class ServiceAccountCreateModel(BaseModel):
    """Internal model for repository creation (includes api_key_hash)"""

    name: str
    description: Optional[str] = None
    company_id: int
    api_key_hash: str


class ServiceAccountUpdate(BaseModel):
    """Model for updating a service account"""

    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ServiceAccountWithApiKey(BaseModel):
    """Service account with plain text API key (only returned on creation)"""

    service_account: ServiceAccount
    api_key: str

    class Config:
        from_attributes = True
