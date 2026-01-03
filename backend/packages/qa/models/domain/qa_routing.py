"""QA routing decision models."""

from enum import StrEnum

from pydantic import BaseModel


class QARoutingReason(StrEnum):
    """Reason for QA routing decision."""

    QUESTION_FLAG = "question_flag"  # use_agent_qa=True on question
    DOCUMENT_SIZE = "document_size"  # Total content exceeds threshold
    DEFAULT = "default"  # No special routing, use regular QA


class QARoutingDecision(BaseModel):
    """Result of QA routing decision."""

    use_agent_qa: bool
    reason: QARoutingReason
    total_char_count: int = 0

    @property
    def is_auto_routed(self) -> bool:
        """Check if routing was automatic (not explicit flag)."""
        return self.use_agent_qa and self.reason == QARoutingReason.DOCUMENT_SIZE
