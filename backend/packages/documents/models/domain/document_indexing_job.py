from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from enum import StrEnum


class DocumentIndexingJobStatus(StrEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentIndexingJobCreateModel(BaseModel):
    """Model for creating a new document indexing job."""

    document_id: int
    status: str = DocumentIndexingJobStatus.QUEUED.value
    worker_message_id: Optional[str] = None
    error_message: Optional[str] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if isinstance(v, DocumentIndexingJobStatus):
            return v.value
        return v


class DocumentIndexingJobUpdateModel(BaseModel):
    """Model for updating a document indexing job."""

    status: Optional[str] = None
    worker_message_id: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if isinstance(v, DocumentIndexingJobStatus):
            return v.value
        return v


class DocumentIndexingJobModel(BaseModel):
    id: int
    document_id: int
    status: DocumentIndexingJobStatus
    worker_message_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if isinstance(v, str):
            # Convert string to enum for domain model
            for status in DocumentIndexingJobStatus:
                if status.value == v:
                    return status
            return v
        return v
