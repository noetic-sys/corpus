"""
Service for tracking usage events.
"""

from typing import Optional
from datetime import datetime

from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.billing.repositories.usage_repository import UsageEventRepository
from packages.billing.models.domain.usage import UsageEvent, UsageEventCreateModel
from packages.billing.models.domain.enums import UsageEventType

logger = get_logger(__name__)


class UsageService:
    """Service for usage event tracking."""

    def __init__(self):
        self.usage_repo = UsageEventRepository()

    @trace_span
    async def track_cell_operation(
        self,
        company_id: int,
        quantity: int,
        user_id: Optional[int] = None,
        matrix_id: Optional[int] = None,
        event_metadata: Optional[dict] = None,
    ) -> UsageEvent:
        """
        Track cell operations (create or update).

        Args:
            company_id: Company performing the operation
            quantity: Number of cells created/updated
            user_id: User who triggered the operation
            matrix_id: Matrix where cells were created
            event_metadata: Additional metadata
        """
        logger.info(
            f"Tracking {quantity} cell operations for company {company_id}",
            extra={
                "company_id": company_id,
                "quantity": quantity,
                "matrix_id": matrix_id,
            },
        )

        event_data = UsageEventCreateModel(
            company_id=company_id,
            user_id=user_id,
            event_type=UsageEventType.CELL_OPERATION,
            quantity=quantity,
            event_metadata={"matrix_id": matrix_id, **(event_metadata or {})},
        )

        event = await self.usage_repo.create(event_data)

        logger.info(
            f"Tracked cell operation event {event.id} (quantity={quantity})",
            extra={
                "event_id": event.id,
                "company_id": company_id,
                "quantity": quantity,
            },
        )

        return event

    @trace_span
    async def track_agentic_qa(
        self,
        company_id: int,
        quantity: int,
        user_id: Optional[int] = None,
        question_id: Optional[int] = None,
        event_metadata: Optional[dict] = None,
    ) -> UsageEvent:
        """
        Track agentic QA usage.

        Called when use_agent_qa is toggled ON for a question,
        tracking the number of cells that will use agentic QA.

        Args:
            company_id: Company enabling agentic QA
            quantity: Number of cells affected
            user_id: User who enabled it
            question_id: Question that had agentic QA enabled
            event_metadata: Additional metadata
        """
        logger.info(
            f"Tracking {quantity} agentic QA cells for company {company_id}",
            extra={
                "company_id": company_id,
                "quantity": quantity,
                "question_id": question_id,
            },
        )

        event_data = UsageEventCreateModel(
            company_id=company_id,
            user_id=user_id,
            event_type=UsageEventType.AGENTIC_QA,
            quantity=quantity,
            event_metadata={"question_id": question_id, **(event_metadata or {})},
        )

        event = await self.usage_repo.create(event_data)

        logger.info(
            f"Tracked agentic QA event {event.id} (quantity={quantity})",
            extra={
                "event_id": event.id,
                "company_id": company_id,
                "quantity": quantity,
            },
        )

        return event

    @trace_span
    async def track_workflow(
        self,
        company_id: int,
        user_id: Optional[int] = None,
        workflow_id: Optional[int] = None,
        event_metadata: Optional[dict] = None,
    ) -> UsageEvent:
        """
        Track a workflow execution.

        Called when a workflow is executed. Always quantity=1.
        """
        logger.info(
            f"Tracking workflow for company {company_id}",
            extra={"company_id": company_id, "workflow_id": workflow_id},
        )

        event_data = UsageEventCreateModel(
            company_id=company_id,
            user_id=user_id,
            event_type=UsageEventType.WORKFLOW,
            quantity=1,
            event_metadata={"workflow_id": workflow_id, **(event_metadata or {})},
        )

        event = await self.usage_repo.create(event_data)

        logger.info(
            f"Tracked workflow event {event.id}",
            extra={
                "event_id": event.id,
                "company_id": company_id,
                "workflow_id": workflow_id,
            },
        )

        return event

    @trace_span
    async def track_agentic_chunking(
        self,
        company_id: int,
        document_id: int,
        user_id: Optional[int] = None,
        chunk_count: Optional[int] = None,
        event_metadata: Optional[dict] = None,
    ) -> UsageEvent:
        """
        Track an agentic (AI-powered) chunking operation.

        Called when a document is processed with the Claude Haiku chunking agent.
        Always quantity=1 (one document).

        Args:
            company_id: Company processing the document
            document_id: Document being chunked
            user_id: User who uploaded the document
            chunk_count: Number of chunks produced
            event_metadata: Additional metadata
        """
        logger.info(
            f"Tracking agentic chunking for company {company_id}",
            extra={
                "company_id": company_id,
                "document_id": document_id,
                "chunk_count": chunk_count,
            },
        )

        event_data = UsageEventCreateModel(
            company_id=company_id,
            user_id=user_id,
            event_type=UsageEventType.AGENTIC_CHUNKING,
            quantity=1,
            event_metadata={
                "document_id": document_id,
                "chunk_count": chunk_count,
                **(event_metadata or {}),
            },
        )

        event = await self.usage_repo.create(event_data)

        logger.info(
            f"Tracked agentic chunking event {event.id}",
            extra={
                "event_id": event.id,
                "company_id": company_id,
                "document_id": document_id,
            },
        )

        return event

    @trace_span
    async def track_storage_upload(
        self,
        company_id: int,
        file_size_bytes: int,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        filename: Optional[str] = None,
        event_metadata: Optional[dict] = None,
    ) -> UsageEvent:
        """
        Track a storage upload event.

        Uses file_size_bytes for quota enforcement (not quantity).
        """
        logger.info(
            f"Tracking storage upload for company {company_id}",
            extra={
                "company_id": company_id,
                "document_id": document_id,
                "file_size_bytes": file_size_bytes,
            },
        )

        event_data = UsageEventCreateModel(
            company_id=company_id,
            user_id=user_id,
            event_type=UsageEventType.STORAGE_UPLOAD,
            quantity=1,
            file_size_bytes=file_size_bytes,
            event_metadata={
                "document_id": document_id,
                "filename": filename,
                **(event_metadata or {}),
            },
        )

        event = await self.usage_repo.create(event_data)

        logger.info(
            f"Tracked storage upload event {event.id}",
            extra={
                "event_id": event.id,
                "company_id": company_id,
                "file_size_bytes": file_size_bytes,
            },
        )

        return event

    @trace_span
    async def refund_agentic_chunking(
        self,
        company_id: int,
        document_id: int,
        original_event_id: int,
    ) -> UsageEvent:
        """
        Refund an agentic chunking credit by creating a -1 quantity event.

        Called when agentic chunking fails after credit was reserved.
        Uses negative quantity so the sum-based quota check still works correctly.
        Preserves audit trail of reservation + refund.

        Args:
            company_id: Company ID
            document_id: Document that failed chunking
            original_event_id: The original reservation event ID (for linking)

        Returns:
            The refund usage event
        """
        logger.info(
            f"Refunding agentic chunking for company {company_id}, document {document_id}"
        )

        event_data = UsageEventCreateModel(
            company_id=company_id,
            event_type=UsageEventType.AGENTIC_CHUNKING,
            quantity=-1,  # Negative to offset the reservation
            event_metadata={
                "document_id": document_id,
                "refund_for_event_id": original_event_id,
                "reason": "chunking_failed",
            },
        )

        event = await self.usage_repo.create(event_data)

        logger.info(
            f"Created refund event {event.id} for original event {original_event_id}",
            extra={
                "event_id": event.id,
                "original_event_id": original_event_id,
                "company_id": company_id,
            },
        )

        return event

    @trace_span
    async def get_user_usage(self, user_id: int, limit: int = 100) -> list[UsageEvent]:
        """Get usage events for a user."""
        return await self.usage_repo.get_by_user(user_id, limit=limit)

    @trace_span
    async def get_company_usage(
        self,
        company_id: int,
        start_date: datetime,
        end_date: datetime,
        event_type: Optional[UsageEventType] = None,
    ) -> list[UsageEvent]:
        """Get usage events for a company within date range."""
        return await self.usage_repo.get_by_company_date_range(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
            event_type=event_type,
        )
