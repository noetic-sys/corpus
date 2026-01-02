"""
Domain models for workflow execution files.
"""

from datetime import datetime
from pydantic import BaseModel, field_validator

from packages.workflows.models.database.execution_file import ExecutionFileType


class ExecutionFileCreateModel(BaseModel):
    """Model for creating an execution file record."""

    execution_id: int
    company_id: int
    file_type: str
    name: str
    storage_path: str
    file_size: int
    mime_type: str | None = None

    @field_validator("file_type", mode="before")
    @classmethod
    def validate_file_type(cls, v):
        if isinstance(v, ExecutionFileType):
            return v.value
        return v


class ExecutionFileModel(BaseModel):
    """Domain model for execution file."""

    id: int
    execution_id: int
    company_id: int
    file_type: ExecutionFileType
    name: str
    storage_path: str
    file_size: int
    mime_type: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("file_type", mode="before")
    @classmethod
    def validate_file_type(cls, v):
        if isinstance(v, str):
            for file_type in ExecutionFileType:
                if file_type.value == v:
                    return file_type
            return v
        return v
