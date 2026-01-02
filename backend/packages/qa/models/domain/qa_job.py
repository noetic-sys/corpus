from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator
from enum import StrEnum


class QAJobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class QAJobCreateModel(BaseModel):
    """Model for creating a new QA job (without auto-generated fields)."""

    matrix_cell_id: int
    status: str = QAJobStatus.QUEUED.value
    worker_message_id: Optional[str] = None
    error_message: Optional[str] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if isinstance(v, QAJobStatus):
            return v.value
        return v


class QAJobUpdateModel(BaseModel):
    """Model for updating a QA job."""

    matrix_cell_id: Optional[int] = None
    status: Optional[str] = None
    worker_message_id: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if isinstance(v, QAJobStatus):
            return v.value
        return v


class QAJobUpdateWithIdModel(BaseModel):
    """Model for bulk updating QA jobs with ID included."""

    id: int
    matrix_cell_id: Optional[int] = None
    status: Optional[str] = None
    worker_message_id: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if isinstance(v, QAJobStatus):
            return v.value
        return v


class QueuePendingCellsResult(BaseModel):
    """Domain model for queue_pending_cells operation result."""

    total_pending_cells: int
    queued: int
    failed: int


class QAJobModel(BaseModel):
    id: int
    matrix_cell_id: int
    status: QAJobStatus
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
            for status in QAJobStatus:
                if status.value == v:
                    return status
            return v
        return v
