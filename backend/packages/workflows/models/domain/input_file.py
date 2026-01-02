"""
Domain models for workflow input files (templates, data files, etc.).
"""

from datetime import datetime
from pydantic import BaseModel


class InputFileCreateModel(BaseModel):
    """Model for creating an input file record."""

    workflow_id: int
    company_id: int
    name: str
    description: str | None = None
    storage_path: str
    file_size: int
    mime_type: str | None = None


class InputFileUpdateModel(BaseModel):
    """Model for updating an input file record."""

    name: str | None = None
    description: str | None = None


class InputFileModel(BaseModel):
    """Domain model for workflow input file."""

    id: int
    workflow_id: int
    company_id: int
    name: str
    description: str | None = None
    storage_path: str
    file_size: int
    mime_type: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
