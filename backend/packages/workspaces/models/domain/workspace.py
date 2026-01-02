from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Workspace(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    company_id: int
    deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WorkspaceCreateModel(BaseModel):
    """Model for creating a new workspace."""

    name: str
    company_id: int
    description: Optional[str] = None


class WorkspaceUpdateModel(BaseModel):
    """Model for updating a workspace."""

    name: Optional[str] = None
    description: Optional[str] = None
