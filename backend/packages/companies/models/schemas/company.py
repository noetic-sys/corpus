from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CompanyCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    description: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    description: Optional[str] = None


class CompanyResponse(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
