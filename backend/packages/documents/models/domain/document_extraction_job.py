from datetime import datetime
from enum import StrEnum
from typing import Optional
from pydantic import BaseModel, field_validator


class DocumentExtractionJobStatus(StrEnum):
    """Job status enum using StrEnum for proper Temporal serialization."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentExtractionJobCreateModel(BaseModel):
    """Model for creating a new document extraction job (without auto-generated fields)."""

    document_id: int
    status: DocumentExtractionJobStatus = DocumentExtractionJobStatus.QUEUED
    worker_message_id: Optional[str] = None
    error_message: Optional[str] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if isinstance(v, DocumentExtractionJobStatus):
            return v
        # Convert string to enum if needed
        if isinstance(v, str):
            return DocumentExtractionJobStatus(v)
        return v


class DocumentExtractionJobUpdateModel(BaseModel):
    """Model for updating a document extraction job."""

    status: Optional[DocumentExtractionJobStatus] = None
    worker_message_id: Optional[str] = None
    error_message: Optional[str] = None
    extracted_content_path: Optional[str] = None
    completed_at: Optional[datetime] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if v is None:
            return v
        if isinstance(v, DocumentExtractionJobStatus):
            return v
        # Convert string to enum if needed
        if isinstance(v, str):
            return DocumentExtractionJobStatus(v)
        return v


class DocumentExtractionJobModel(BaseModel):
    id: int
    document_id: int
    status: DocumentExtractionJobStatus
    worker_message_id: Optional[str] = None
    error_message: Optional[str] = None
    extracted_content_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if isinstance(v, str):
            # Convert string to enum for domain model
            for status in DocumentExtractionJobStatus:
                if status.value == v:
                    return status
            return v
        return v
