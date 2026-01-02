"""
QA routing service.

Determines whether to use agent-based QA or regular QA based on:
1. Question configuration (use_agent_qa flag)

TODO: Add document size-based routing when we have content_length in documents table
"""

from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class QARoutingService:
    """Service for determining QA processing route."""

    @staticmethod
    @trace_span
    def should_use_agent_qa(question_use_agent_qa: bool) -> bool:
        """
        Determine if agent-based QA should be used.

        Currently only checks question.use_agent_qa flag.

        TODO: Add document size check once we have content_length in documents table:
        - Query document.content_length from DB (don't load full content)
        - If sum(content_lengths) > threshold, use agent QA
        - Threshold: ~400K chars (~100K tokens)

        Args:
            question_use_agent_qa: Whether question requires agent QA

        Returns:
            True if agent QA should be used, False otherwise
        """
        if question_use_agent_qa:
            logger.info("Using agent QA: question.use_agent_qa=True")
            return True

        # Use regular QA
        logger.info("Using regular QA: question.use_agent_qa=False")
        return False


def get_qa_routing_service() -> QARoutingService:
    """Get QA routing service instance."""
    return QARoutingService()
