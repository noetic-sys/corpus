from __future__ import annotations
from enum import StrEnum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TriggerType(StrEnum):
    MANUAL = "manual"


class OutputType(StrEnum):
    POWERPOINT = "powerpoint"
    MARKDOWN = "markdown"
    EXCEL = "excel"
    DOCX = "docx"
    PDF = "pdf"


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowModel(BaseModel):
    """Domain model for a workflow."""

    id: int
    company_id: int
    name: str
    description: Optional[str] = None

    # Triggering
    trigger_type: TriggerType

    # Source workspace
    workspace_id: int

    # Output
    output_type: OutputType

    # State
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowCreateModel(BaseModel):
    """Model for creating a new workflow."""

    company_id: int
    name: str
    description: Optional[str] = None

    trigger_type: TriggerType
    workspace_id: int

    output_type: OutputType


class WorkflowUpdateModel(BaseModel):
    """Model for updating a workflow."""

    name: Optional[str] = None
    description: Optional[str] = None

    trigger_type: Optional[TriggerType] = None

    output_type: Optional[OutputType] = None
