from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from packages.qa.models.domain.qa_job import QAJobStatus


# QA Job schemas
class QAJobBase(BaseModel):
    status: QAJobStatus = QAJobStatus.QUEUED.value
    worker_message_id: Optional[str] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class QAJobUpdate(BaseModel):
    status: Optional[QAJobStatus] = None
    worker_message_id: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class QAJobResponse(QAJobBase):
    id: int
    matrix_cell_id: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )


class QueuePendingCellsRequest(BaseModel):
    """Request schema for queue_pending_cells operation."""

    matrix_id: Optional[int] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class QueuePendingCellsResponse(BaseModel):
    """Response schema for queue_pending_cells operation."""

    total_pending_cells: int
    queued: int
    failed: int

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
