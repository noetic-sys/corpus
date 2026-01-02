"""update_anthropic_models_sonnet_45

Revision ID: 814b0770e36e
Revises: bcdc79716df0
Create Date: 2025-10-02 18:11:52.392601

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '814b0770e36e'
down_revision: Union[str, Sequence[str], None] = 'bcdc79716df0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new Anthropic models and deprecate old ones."""

    # Deprecate old Claude 3 models (keep them but set enabled=false)
    op.execute("""
        UPDATE ai_models
        SET enabled = false
        WHERE model_name IN (
            'claude-3-5-sonnet-20240620',  -- Old Sonnet 3.5
            'claude-3-opus-20240229',      -- Claude 3 Opus
            'claude-3-sonnet-20240229',    -- Claude 3 Sonnet
            'claude-3-haiku-20240307'      -- Claude 3 Haiku
        )
    """)

    # Insert new Anthropic models (provider_id = 2)
    op.execute("""
        INSERT INTO ai_models (provider_id, model_name, display_name, default_temperature, default_max_tokens, enabled)
        VALUES
            (2, 'claude-sonnet-4-5-20250929', 'Claude Sonnet 4.5', 0.7, 4096, true),
            (2, 'claude-sonnet-4-20250514', 'Claude Sonnet 4', 0.7, 4096, true),
            (2, 'claude-3-7-sonnet-20250219', 'Claude 3.7 Sonnet', 0.7, 4096, true),
            (2, 'claude-opus-4-1-20250805', 'Claude Opus 4.1', 0.7, 4096, true),
            (2, 'claude-opus-4-20250514', 'Claude Opus 4', 0.7, 4096, true),
            (2, 'claude-3-5-haiku-20241022', 'Claude 3.5 Haiku', 0.7, 4096, true)
    """)


def downgrade() -> None:
    """Re-enable old models and disable new ones."""

    # Re-enable old models
    op.execute("""
        UPDATE ai_models
        SET enabled = true
        WHERE model_name IN (
            'claude-3-5-sonnet-20240620',
            'claude-3-opus-20240229',
            'claude-3-sonnet-20240229',
            'claude-3-haiku-20240307'
        )
    """)

    # Disable new models
    op.execute("""
        UPDATE ai_models
        SET enabled = false
        WHERE model_name IN (
            'claude-sonnet-4-5-20250929',
            'claude-sonnet-4-20250514',
            'claude-3-7-sonnet-20250219',
            'claude-opus-4-1-20250805',
            'claude-opus-4-20250514',
            'claude-3-5-haiku-20241022'
        )
    """)
