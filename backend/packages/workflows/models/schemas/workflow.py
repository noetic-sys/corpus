from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class WorkflowCreate(BaseModel):
    """Request to create a workflow"""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_type: str = Field(..., description="Trigger type (manual)")
    workspace_id: int = Field(..., description="Workspace ID")
    output_type: str = Field(..., description="Output type (e.g., excel, pdf, docx)")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class WorkflowUpdate(BaseModel):
    """Request to update a workflow"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    output_type: Optional[str] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class WorkflowResponse(BaseModel):
    """Response model for workflow"""

    id: int
    company_id: int
    name: str
    description: Optional[str] = None
    trigger_type: str
    workspace_id: int
    output_type: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )
