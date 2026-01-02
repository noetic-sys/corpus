"""
API schemas for workflow input files.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class InputFileResponse(BaseModel):
    """Response model for workflow input file."""

    id: int
    workflow_id: int
    name: str
    description: str | None = None
    file_size: int
    mime_type: str | None = None
    created_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
