"""Chunking strategy enum for tiered document processing."""

from enum import Enum


class ChunkingStrategy(str, Enum):
    """
    Document chunking strategies, ordered by cost/quality.

    Lower tiers use cheaper strategies, higher tiers get AI-powered chunking.
    """

    NONE = "none"
    """No chunking - full document as single chunk. Not recommended."""

    FIXED_SIZE = "fixed_size"
    """Split every N characters with overlap. Fast, free, low quality."""

    SENTENCE = "sentence"
    """Split on sentence boundaries. Free, decent quality."""

    PARAGRAPH = "paragraph"
    """Split on paragraph boundaries. Free, good for structured docs."""

    AGENTIC = "agentic"
    """Claude Haiku agent chunking. Costs ~$0.02-0.10/doc, best quality."""

    @classmethod
    def get_default_for_tier(cls, tier: str) -> "ChunkingStrategy":
        """
        Get the default chunking strategy for a subscription tier.

        Args:
            tier: Subscription tier string (free, starter, pro, business, enterprise)

        Returns:
            Default ChunkingStrategy for that tier
        """
        # Import here to avoid circular imports
        from packages.billing.models.domain.enums import (  # noqa: PLC0415
            SubscriptionTier,
        )

        tier_defaults = {
            SubscriptionTier.FREE: cls.FIXED_SIZE,
            SubscriptionTier.STARTER: cls.SENTENCE,
            SubscriptionTier.PROFESSIONAL: cls.AGENTIC,
            SubscriptionTier.BUSINESS: cls.AGENTIC,
            SubscriptionTier.ENTERPRISE: cls.AGENTIC,
        }

        try:
            tier_enum = SubscriptionTier(tier)
            return tier_defaults.get(tier_enum, cls.FIXED_SIZE)
        except ValueError:
            return cls.FIXED_SIZE

    def is_agentic(self) -> bool:
        """Check if this strategy uses AI/costs money."""
        return self == ChunkingStrategy.AGENTIC

    def is_naive(self) -> bool:
        """Check if this strategy is free/in-process."""
        return self in (
            ChunkingStrategy.FIXED_SIZE,
            ChunkingStrategy.SENTENCE,
            ChunkingStrategy.PARAGRAPH,
        )
