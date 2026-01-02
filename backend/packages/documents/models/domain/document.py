from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator
from enum import StrEnum


class ExtractionStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentModel(BaseModel):
    id: int
    filename: str
    storage_key: str
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    checksum: str
    company_id: int

    # Extraction fields
    extracted_content_path: Optional[str] = None
    extraction_status: ExtractionStatus = ExtractionStatus.PENDING
    extraction_started_at: Optional[datetime] = None
    extraction_completed_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("extraction_status", mode="before")
    @classmethod
    def validate_extraction_status(cls, v):
        if isinstance(v, str):
            # Convert string to enum for domain model
            for status in ExtractionStatus:
                if status.value == v:
                    return status
            return v
        return v


class DocumentCreateModel(BaseModel):
    """Model for creating a new document."""

    filename: str
    storage_key: str
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    checksum: str
    company_id: int
    extraction_status: str = ExtractionStatus.PENDING.value

    @field_validator("extraction_status", mode="before")
    @classmethod
    def validate_extraction_status(cls, v):
        if isinstance(v, ExtractionStatus):
            return v.value
        return v


class DocumentUpdateModel(BaseModel):
    """Model for updating a document."""

    filename: Optional[str] = None
    storage_key: Optional[str] = None
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    company_id: Optional[int] = None
    extraction_status: Optional[str] = None
    extracted_content_path: Optional[str] = None
    extraction_started_at: Optional[datetime] = None
    extraction_completed_at: Optional[datetime] = None

    @field_validator("extraction_status", mode="before")
    @classmethod
    def validate_extraction_status(cls, v):
        if isinstance(v, ExtractionStatus):
            return v.value
        return v


class DocumentExtractionStatsModel(BaseModel):
    """Model for document extraction statistics."""

    total_documents: int
    pending: int
    processing: int
    completed: int
    failed: int
