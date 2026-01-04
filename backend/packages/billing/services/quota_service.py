"""
Service for quota enforcement and checking.

This is the critical service that prevents usage beyond subscription limits.
"""

from datetime import datetime
from fastapi import HTTPException, status

from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.billing.repositories.subscription_repository import SubscriptionRepository
from packages.billing.repositories.usage_repository import UsageEventRepository
from packages.billing.models.domain.usage import (
    QuotaCheck,
    QuotaReservationResult,
    UsageStats,
    UsageEventCreateModel,
)
from packages.billing.models.domain.enums import SubscriptionTier, UsageEventType

logger = get_logger(__name__)


class QuotaService:
    """Service for quota enforcement."""

    def __init__(self):
        self.subscription_repo = SubscriptionRepository()
        self.usage_repo = UsageEventRepository()

    async def _get_subscription_or_raise(self, company_id: int):
        """Get subscription and validate access."""
        subscription = await self.subscription_repo.get_by_company_id(company_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="No active subscription found. Please subscribe to continue.",
            )

        if not subscription.has_access():
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Subscription is {subscription.status.value}. Please update billing.",
            )

        return subscription

    def _build_quota_check(
        self, metric_name: str, current: int, limit: int, period_end: datetime
    ) -> QuotaCheck:
        """Build a QuotaCheck response."""
        remaining = limit - current
        percentage_used = (current / limit * 100) if limit else 0

        return QuotaCheck(
            allowed=True,
            metric_name=metric_name,
            current_usage=current,
            limit=limit,
            remaining=remaining,
            percentage_used=percentage_used,
            warning_threshold_reached=(percentage_used >= 80),
            period_type="monthly",
            period_end=period_end,
        )

    @trace_span
    async def check_cell_operation_quota(self, company_id: int) -> QuotaCheck:
        """
        Check if company can perform another cell operation.

        Raises HTTPException if quota exceeded.
        """
        subscription = await self._get_subscription_or_raise(company_id)
        limits = subscription.tier.get_quota_limits()
        limit = limits["cell_operations_per_month"]

        current = await self.usage_repo.get_period_count(
            company_id=company_id,
            event_type=UsageEventType.CELL_OPERATION,
            start_date=subscription.current_period_start,
            end_date=subscription.current_period_end,
        )

        if current >= limit:
            logger.warning(
                f"Company {company_id} exceeded cell operations quota",
                extra={"company_id": company_id, "current": current, "limit": limit},
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly cell operations limit reached ({limit:,}). Upgrade your plan for more.",
            )

        return self._build_quota_check(
            "cell_operations", current, limit, subscription.current_period_end
        )

    @trace_span
    async def check_agentic_qa_quota(self, company_id: int) -> QuotaCheck:
        """
        Check if company can run another agentic QA.

        Raises HTTPException if quota exceeded.
        """
        subscription = await self._get_subscription_or_raise(company_id)
        limits = subscription.tier.get_quota_limits()
        limit = limits["agentic_qa_per_month"]

        current = await self.usage_repo.get_period_count(
            company_id=company_id,
            event_type=UsageEventType.AGENTIC_QA,
            start_date=subscription.current_period_start,
            end_date=subscription.current_period_end,
        )

        if current >= limit:
            logger.warning(
                f"Company {company_id} exceeded agentic QA quota",
                extra={"company_id": company_id, "current": current, "limit": limit},
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly agentic QA limit reached ({limit:,}). Upgrade your plan for more.",
            )

        return self._build_quota_check(
            "agentic_qa", current, limit, subscription.current_period_end
        )

    @trace_span
    async def check_workflow_quota(self, company_id: int) -> QuotaCheck:
        """
        Check if company can run another workflow.

        Raises HTTPException if quota exceeded.
        """
        subscription = await self._get_subscription_or_raise(company_id)
        limits = subscription.tier.get_quota_limits()
        limit = limits["workflows_per_month"]

        current = await self.usage_repo.get_period_count(
            company_id=company_id,
            event_type=UsageEventType.WORKFLOW,
            start_date=subscription.current_period_start,
            end_date=subscription.current_period_end,
        )

        if current >= limit:
            logger.warning(
                f"Company {company_id} exceeded workflow quota",
                extra={"company_id": company_id, "current": current, "limit": limit},
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly workflow limit reached ({limit:,}). Upgrade your plan for more.",
            )

        return self._build_quota_check(
            "workflows", current, limit, subscription.current_period_end
        )

    @trace_span
    async def check_agentic_chunking_quota(self, company_id: int) -> QuotaCheck:
        """
        Check if company can use another agentic chunking credit.

        Raises HTTPException if quota exceeded.
        """
        subscription = await self._get_subscription_or_raise(company_id)
        limits = subscription.tier.get_quota_limits()
        limit = limits["agentic_chunking_per_month"]

        current = await self.usage_repo.get_period_count(
            company_id=company_id,
            event_type=UsageEventType.AGENTIC_CHUNKING,
            start_date=subscription.current_period_start,
            end_date=subscription.current_period_end,
        )

        if current >= limit:
            logger.warning(
                f"Company {company_id} exceeded agentic chunking quota",
                extra={"company_id": company_id, "current": current, "limit": limit},
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly AI document processing limit reached ({limit:,}). Documents will use standard processing, or upgrade your plan.",
            )

        return self._build_quota_check(
            "agentic_chunking", current, limit, subscription.current_period_end
        )

    @trace_span
    async def check_document_quota(self, company_id: int) -> QuotaCheck:
        """
        Check if company can upload another document.

        Raises HTTPException if quota exceeded.
        """
        subscription = await self._get_subscription_or_raise(company_id)
        limits = subscription.tier.get_quota_limits()
        limit = limits["documents_per_month"]

        current = await self.usage_repo.get_document_count_for_period(
            company_id=company_id,
            start_date=subscription.current_period_start,
            end_date=subscription.current_period_end,
        )

        if current >= limit:
            logger.warning(
                f"Company {company_id} exceeded document upload quota",
                extra={"company_id": company_id, "current": current, "limit": limit},
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly document upload limit reached ({limit:,}). Upgrade your plan for more.",
            )

        return self._build_quota_check(
            "documents", current, limit, subscription.current_period_end
        )

    @trace_span
    async def check_storage_quota(
        self, company_id: int, file_size_bytes: int
    ) -> QuotaCheck:
        """
        Check if company can upload more data.

        Raises HTTPException if quota exceeded.
        """
        subscription = await self._get_subscription_or_raise(company_id)
        limits = subscription.tier.get_quota_limits()
        limit = limits["storage_bytes_per_month"]

        current = await self.usage_repo.get_storage_bytes_for_period(
            company_id=company_id,
            start_date=subscription.current_period_start,
            end_date=subscription.current_period_end,
        )

        if current + file_size_bytes > limit:
            current_mb = current / (1024 * 1024)
            adding_mb = file_size_bytes / (1024 * 1024)
            limit_mb = limit / (1024 * 1024)

            logger.warning(
                f"Company {company_id} would exceed storage quota",
                extra={
                    "company_id": company_id,
                    "current_bytes": current,
                    "adding_bytes": file_size_bytes,
                    "limit_bytes": limit,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly storage limit would be exceeded. Current: {current_mb:.1f} MB, adding {adding_mb:.1f} MB, limit: {limit_mb:.0f} MB. Upgrade for more storage.",
            )

        return self._build_quota_check(
            "storage_bytes", current, limit, subscription.current_period_end
        )

    @trace_span
    async def reserve_agentic_chunking_if_available(
        self, company_id: int, document_id: int
    ) -> QuotaReservationResult:
        """
        Atomically check quota and reserve agentic chunking credit.

        Uses advisory lock to serialize concurrent requests for the same company.

        Args:
            company_id: Company ID
            document_id: Document ID for tracking

        Returns:
            QuotaReservationResult with reservation status and details
        """
        # Acquire advisory lock - serializes quota operations for this company
        await self.usage_repo.acquire_company_quota_lock(company_id)

        subscription = await self.subscription_repo.get_by_company_id(company_id)
        if not subscription or not subscription.has_access():
            return QuotaReservationResult(
                reserved=False,
                usage_event_id=None,
                current_usage=0,
                limit=0,
                tier=SubscriptionTier.FREE,
            )

        limits = subscription.tier.get_quota_limits()
        limit = limits["agentic_chunking_per_month"]

        current = await self.usage_repo.get_period_count(
            company_id=company_id,
            event_type=UsageEventType.AGENTIC_CHUNKING,
            start_date=subscription.current_period_start,
            end_date=subscription.current_period_end,
        )

        if current >= limit:
            logger.info(
                f"Company {company_id} agentic chunking quota exceeded ({current}/{limit})",
                extra={"company_id": company_id, "current": current, "limit": limit},
            )
            return QuotaReservationResult(
                reserved=False,
                usage_event_id=None,
                current_usage=current,
                limit=limit,
                tier=subscription.tier,
            )

        # Quota available - create usage event
        event_data = UsageEventCreateModel(
            company_id=company_id,
            event_type=UsageEventType.AGENTIC_CHUNKING,
            quantity=1,
            event_metadata={"document_id": document_id},
        )
        event = await self.usage_repo.create(event_data)

        logger.info(
            f"Reserved agentic chunking for company {company_id}, "
            f"document {document_id}, event_id={event.id} ({current + 1}/{limit})",
            extra={
                "company_id": company_id,
                "document_id": document_id,
                "event_id": event.id,
            },
        )

        return QuotaReservationResult(
            reserved=True,
            usage_event_id=event.id,
            current_usage=current + 1,
            limit=limit,
            tier=subscription.tier,
        )

    @trace_span
    async def get_usage_stats(self, company_id: int) -> UsageStats:
        """
        Get complete usage statistics for a company.
        """
        subscription = await self.subscription_repo.get_by_company_id(company_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No subscription found"
            )

        limits = subscription.tier.get_quota_limits()

        cell_ops = await self.usage_repo.get_period_count(
            company_id=company_id,
            event_type=UsageEventType.CELL_OPERATION,
            start_date=subscription.current_period_start,
            end_date=subscription.current_period_end,
        )

        agentic_qa = await self.usage_repo.get_period_count(
            company_id=company_id,
            event_type=UsageEventType.AGENTIC_QA,
            start_date=subscription.current_period_start,
            end_date=subscription.current_period_end,
        )

        workflows = await self.usage_repo.get_period_count(
            company_id=company_id,
            event_type=UsageEventType.WORKFLOW,
            start_date=subscription.current_period_start,
            end_date=subscription.current_period_end,
        )

        storage_bytes = await self.usage_repo.get_storage_bytes_for_period(
            company_id=company_id,
            start_date=subscription.current_period_start,
            end_date=subscription.current_period_end,
        )

        agentic_chunking = await self.usage_repo.get_period_count(
            company_id=company_id,
            event_type=UsageEventType.AGENTIC_CHUNKING,
            start_date=subscription.current_period_start,
            end_date=subscription.current_period_end,
        )

        documents = await self.usage_repo.get_document_count_for_period(
            company_id=company_id,
            start_date=subscription.current_period_start,
            end_date=subscription.current_period_end,
        )

        return UsageStats(
            company_id=company_id,
            tier=subscription.tier,
            cell_operations=cell_ops,
            cell_operations_limit=limits["cell_operations_per_month"],
            agentic_qa=agentic_qa,
            agentic_qa_limit=limits["agentic_qa_per_month"],
            workflows=workflows,
            workflows_limit=limits["workflows_per_month"],
            storage_bytes=storage_bytes,
            storage_bytes_limit=limits["storage_bytes_per_month"],
            agentic_chunking=agentic_chunking,
            agentic_chunking_limit=limits["agentic_chunking_per_month"],
            documents=documents,
            documents_limit=limits["documents_per_month"],
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
        )
