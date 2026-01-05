"""update_ai_models_jan_2026

Revision ID: ab247672d522
Revises: 5bd5e08b35df
Create Date: 2026-01-05 18:42:31.785223

Updates AI models based on January 2026 provider offerings:
- OpenAI: Add GPT-4.1 series, o-series reasoning models; deprecate GPT-4/3.5
- Anthropic: Add Claude Opus 4.5, Haiku 4.5
- Google: Add Gemini 2.0 Flash variants, Gemini 3 series
- xAI: Add Grok fast variants, Grok 4.1 beta
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'ab247672d522'
down_revision: Union[str, Sequence[str], None] = '5bd5e08b35df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new models and deprecate legacy ones."""

    # =========================================================================
    # DEPRECATE legacy OpenAI models
    # =========================================================================
    op.execute("""
        UPDATE ai_models
        SET enabled = false
        WHERE model_name IN (
            'gpt-4-turbo',
            'gpt-4',
            'gpt-3.5-turbo'
        )
    """)

    # =========================================================================
    # ADD new OpenAI models (provider_id = 1)
    # GPT-4.1 series replaces GPT-4o as flagship
    # o-series are reasoning models
    # =========================================================================
    op.execute("""
        INSERT INTO ai_models (provider_id, model_name, display_name, default_temperature, default_max_tokens, enabled)
        VALUES
            (1, 'gpt-4.1', 'GPT-4.1', 0.7, NULL, true),
            (1, 'gpt-4.1-mini', 'GPT-4.1 Mini', 0.7, NULL, true),
            (1, 'gpt-4.1-nano', 'GPT-4.1 Nano', 0.7, NULL, true),
            (1, 'o1', 'o1', 0.7, NULL, true),
            (1, 'o3', 'o3', 0.7, NULL, true),
            (1, 'o3-mini', 'o3 Mini', 0.7, NULL, true)
    """)

    # =========================================================================
    # ADD new Anthropic models (provider_id = 2)
    # Opus 4.5 is the latest flagship
    # Haiku 4.5 is fast/cheap option
    # =========================================================================
    op.execute("""
        INSERT INTO ai_models (provider_id, model_name, display_name, default_temperature, default_max_tokens, enabled)
        VALUES
            (2, 'claude-opus-4-5-20251101', 'Claude Opus 4.5', 0.7, 4096, true),
            (2, 'claude-haiku-4-5-20251015', 'Claude Haiku 4.5', 0.7, 4096, true)
    """)

    # =========================================================================
    # ADD new Google models (provider_id = 3)
    # Gemini 2.0 Flash variants are budget-friendly
    # Gemini 3 series is newest (preview)
    # =========================================================================
    op.execute("""
        INSERT INTO ai_models (provider_id, model_name, display_name, default_temperature, default_max_tokens, enabled)
        VALUES
            (3, 'gemini-2.0-flash', 'Gemini 2.0 Flash', 0.7, NULL, true),
            (3, 'gemini-2.0-flash-lite', 'Gemini 2.0 Flash-Lite', 0.7, NULL, true),
            (3, 'gemini-3-pro', 'Gemini 3 Pro', 0.7, NULL, true),
            (3, 'gemini-3-flash', 'Gemini 3 Flash', 0.7, NULL, true)
    """)

    # =========================================================================
    # ADD new xAI models (provider_id = 4)
    # Fast variants for speed-optimized inference
    # Grok 4.1 beta is latest
    # =========================================================================
    op.execute("""
        INSERT INTO ai_models (provider_id, model_name, display_name, default_temperature, default_max_tokens, enabled)
        VALUES
            (4, 'grok-3-fast', 'Grok 3 Fast', 0.7, NULL, true),
            (4, 'grok-3-mini-fast', 'Grok 3 Mini Fast', 0.7, NULL, true),
            (4, 'grok-4.1-beta', 'Grok 4.1 Beta', 0.7, NULL, true)
    """)


def downgrade() -> None:
    """Remove new models and re-enable deprecated ones."""

    # Re-enable deprecated OpenAI models
    op.execute("""
        UPDATE ai_models
        SET enabled = true
        WHERE model_name IN (
            'gpt-4-turbo',
            'gpt-4',
            'gpt-3.5-turbo'
        )
    """)

    # Remove new OpenAI models
    op.execute("""
        DELETE FROM ai_models
        WHERE model_name IN (
            'gpt-4.1',
            'gpt-4.1-mini',
            'gpt-4.1-nano',
            'o1',
            'o3',
            'o3-mini'
        )
    """)

    # Remove new Anthropic models
    op.execute("""
        DELETE FROM ai_models
        WHERE model_name IN (
            'claude-opus-4-5-20251101',
            'claude-haiku-4-5-20251015'
        )
    """)

    # Remove new Google models
    op.execute("""
        DELETE FROM ai_models
        WHERE model_name IN (
            'gemini-2.0-flash',
            'gemini-2.0-flash-lite',
            'gemini-3-pro',
            'gemini-3-flash'
        )
    """)

    # Remove new xAI models
    op.execute("""
        DELETE FROM ai_models
        WHERE model_name IN (
            'grok-3-fast',
            'grok-3-mini-fast',
            'grok-4.1-beta'
        )
    """)
