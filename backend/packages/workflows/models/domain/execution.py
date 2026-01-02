from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

from packages.workflows.models.domain.workflow import ExecutionStatus


class WorkflowExecutionModel(BaseModel):
    """Domain model for a workflow execution."""

    id: int
    workflow_id: int
    company_id: int

    # Execution details
    trigger_type: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Results
    status: ExecutionStatus
    output_size_bytes: Optional[int] = None

    # Debugging
    error_message: Optional[str] = None
    execution_log: Optional[Dict[str, Any]] = None

    # Soft delete
    deleted: bool = False

    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowExecutionCreateModel(BaseModel):
    """Model for creating a workflow execution record."""

    workflow_id: int
    company_id: int
    trigger_type: Optional[str] = None
    started_at: datetime
    status: ExecutionStatus


class WorkflowExecutionUpdateModel(BaseModel):
    """Model for updating a workflow execution."""

    completed_at: Optional[datetime] = None
    status: Optional[ExecutionStatus] = None
    output_size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    execution_log: Optional[Dict[str, Any]] = None
