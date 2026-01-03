"""Unit tests for QARoutingService."""

import pytest
from unittest.mock import patch

from packages.qa.services.qa_routing_service import QARoutingService
from packages.qa.models.domain.qa_routing import QARoutingReason


class TestQARoutingService:
    """Tests for QARoutingService.should_use_agent_qa()."""

    def test_explicit_flag_true_uses_agent_qa(self):
        """When question.use_agent_qa=True, should use agent QA regardless of size."""
        decision = QARoutingService.should_use_agent_qa(
            question_use_agent_qa=True,
            total_char_count=1000,  # Small doc
        )

        assert decision.use_agent_qa is True
        assert decision.reason == QARoutingReason.QUESTION_FLAG
        assert decision.total_char_count == 1000
        assert decision.is_auto_routed is False

    def test_explicit_flag_false_small_doc_uses_regular_qa(self):
        """When flag=False and small doc, should use regular QA."""
        decision = QARoutingService.should_use_agent_qa(
            question_use_agent_qa=False,
            total_char_count=100_000,  # 100K chars, under 400K threshold
        )

        assert decision.use_agent_qa is False
        assert decision.reason == QARoutingReason.DEFAULT
        assert decision.total_char_count == 100_000
        assert decision.is_auto_routed is False

    def test_large_doc_auto_routes_to_agent_qa(self):
        """When document exceeds threshold, should auto-route to agent QA."""
        # Default threshold is 400K
        decision = QARoutingService.should_use_agent_qa(
            question_use_agent_qa=False,
            total_char_count=500_000,  # 500K chars, over 400K threshold
        )

        assert decision.use_agent_qa is True
        assert decision.reason == QARoutingReason.DOCUMENT_SIZE
        assert decision.total_char_count == 500_000
        assert decision.is_auto_routed is True

    def test_threshold_boundary_exactly_at_threshold(self):
        """At exactly threshold, should use regular QA (not strictly greater)."""
        with patch(
            "packages.qa.services.qa_routing_service.settings"
        ) as mock_settings:
            mock_settings.agent_qa_char_threshold = 400_000

            decision = QARoutingService.should_use_agent_qa(
                question_use_agent_qa=False,
                total_char_count=400_000,  # Exactly at threshold
            )

            assert decision.use_agent_qa is False
            assert decision.reason == QARoutingReason.DEFAULT

    def test_threshold_boundary_just_over(self):
        """Just over threshold should trigger agent QA."""
        with patch(
            "packages.qa.services.qa_routing_service.settings"
        ) as mock_settings:
            mock_settings.agent_qa_char_threshold = 400_000

            decision = QARoutingService.should_use_agent_qa(
                question_use_agent_qa=False,
                total_char_count=400_001,  # Just over threshold
            )

            assert decision.use_agent_qa is True
            assert decision.reason == QARoutingReason.DOCUMENT_SIZE
            assert decision.is_auto_routed is True

    def test_zero_char_count_uses_regular_qa(self):
        """Zero char count (no documents?) should use regular QA."""
        decision = QARoutingService.should_use_agent_qa(
            question_use_agent_qa=False,
            total_char_count=0,
        )

        assert decision.use_agent_qa is False
        assert decision.reason == QARoutingReason.DEFAULT

    def test_default_char_count_when_not_provided(self):
        """When char count not provided, defaults to 0."""
        decision = QARoutingService.should_use_agent_qa(
            question_use_agent_qa=False,
        )

        assert decision.use_agent_qa is False
        assert decision.total_char_count == 0

    def test_custom_threshold_from_settings(self):
        """Should respect custom threshold from settings."""
        with patch(
            "packages.qa.services.qa_routing_service.settings"
        ) as mock_settings:
            mock_settings.agent_qa_char_threshold = 100_000  # Lower threshold

            decision = QARoutingService.should_use_agent_qa(
                question_use_agent_qa=False,
                total_char_count=150_000,  # Over custom threshold
            )

            assert decision.use_agent_qa is True
            assert decision.reason == QARoutingReason.DOCUMENT_SIZE

    def test_explicit_flag_takes_precedence_over_size(self):
        """Explicit flag should be checked first, before size."""
        decision = QARoutingService.should_use_agent_qa(
            question_use_agent_qa=True,
            total_char_count=500_000,  # Large doc
        )

        # Should report QUESTION_FLAG, not DOCUMENT_SIZE
        assert decision.reason == QARoutingReason.QUESTION_FLAG
        assert decision.is_auto_routed is False
