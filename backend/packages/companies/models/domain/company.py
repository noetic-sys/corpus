from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Company(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None
    description: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    deleted: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyCreateModel(BaseModel):
    """Model for creating a new company."""

    name: str
    domain: Optional[str] = None
    description: Optional[str] = None


class CompanyUpdateModel(BaseModel):
    """Model for updating a company."""

    name: Optional[str] = None
    domain: Optional[str] = None
    description: Optional[str] = None
    stripe_customer_id: Optional[str] = None
