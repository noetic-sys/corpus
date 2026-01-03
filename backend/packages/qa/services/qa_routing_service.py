"""
QA routing service.

Determines whether to use agent-based QA or regular QA based on:
1. Question configuration (use_agent_qa flag)
2. Document size (auto-route to agent QA if content exceeds threshold)
"""

from common.core.config import settings
from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.qa.models.domain.qa_routing import (
    QARoutingDecision,
    QARoutingReason,
)

logger = get_logger(__name__)


class QARoutingService:
    """Service for determining QA processing route."""

    @staticmethod
    @trace_span
    def should_use_agent_qa(
        question_use_agent_qa: bool,
        total_char_count: int = 0,
    ) -> QARoutingDecision:
        """
        Determine if agent-based QA should be used.

        Checks in order:
        1. If question.use_agent_qa is True, use agent QA
        2. If total document char count exceeds threshold, use agent QA
        3. Otherwise, use regular QA

        Args:
            question_use_agent_qa: Whether question explicitly requires agent QA
            total_char_count: Sum of extracted_text_char_count for all documents

        Returns:
            QARoutingDecision with use_agent_qa flag, reason, and char count
        """
        threshold = settings.agent_qa_char_threshold

        # Check explicit flag first
        if question_use_agent_qa:
            logger.info("Using agent QA: question.use_agent_qa=True")
            return QARoutingDecision(
                use_agent_qa=True,
                reason=QARoutingReason.QUESTION_FLAG,
                total_char_count=total_char_count,
            )

        # Check document size threshold
        if total_char_count > threshold:
            logger.info(
                f"Using agent QA: document size ({total_char_count:,} chars) "
                f"exceeds threshold ({threshold:,} chars)"
            )
            return QARoutingDecision(
                use_agent_qa=True,
                reason=QARoutingReason.DOCUMENT_SIZE,
                total_char_count=total_char_count,
            )

        # Use regular QA
        logger.info(
            f"Using regular QA: size ({total_char_count:,} chars) "
            f"within threshold ({threshold:,} chars)"
        )
        return QARoutingDecision(
            use_agent_qa=False,
            reason=QARoutingReason.DEFAULT,
            total_char_count=total_char_count,
        )


def get_qa_routing_service() -> QARoutingService:
    """Get QA routing service instance."""
    return QARoutingService()
