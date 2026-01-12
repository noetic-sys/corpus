"""fix_openrouter_model_ids

Revision ID: a137f5f7fc3f
Revises: ab247672d522
Create Date: 2026-01-12 13:41:41.814402

Fix model names to match actual OpenRouter model IDs.
OpenRouter API: https://openrouter.ai/api/v1/models

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a137f5f7fc3f'
down_revision: Union[str, Sequence[str], None] = 'ab247672d522'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Mapping of wrong model names to correct OpenRouter model names
# Format: (old_name, new_name)
# Provider prefix (anthropic/, openai/, google/, x-ai/) is added by code based on provider_id
ANTHROPIC_FIXES = [
    ('claude-sonnet-4-5-20250929', 'claude-sonnet-4.5'),
    ('claude-sonnet-4-20250514', 'claude-sonnet-4'),
    ('claude-3-7-sonnet-20250219', 'claude-3.7-sonnet'),
    ('claude-opus-4-1-20250805', 'claude-opus-4.1'),
    ('claude-opus-4-20250514', 'claude-opus-4'),
    ('claude-3-5-haiku-20241022', 'claude-3.5-haiku'),
    ('claude-opus-4-5-20251101', 'claude-opus-4.5'),
    ('claude-haiku-4-5-20251015', 'claude-haiku-4.5'),
    ('claude-3-5-sonnet-20241022', 'claude-3.5-sonnet'),
    ('claude-3-haiku-20240307', 'claude-3-haiku'),
]

GOOGLE_FIXES = [
    ('gemini-2.0-flash', 'gemini-2.0-flash-001'),
    ('gemini-2.0-flash-lite', 'gemini-2.0-flash-lite-001'),
    ('gemini-3-pro', 'gemini-3-pro-preview'),
    ('gemini-3-flash', 'gemini-3-flash-preview'),
]

XAI_FIXES = [
    ('grok-4.1-beta', 'grok-4.1-fast'),
]

# Models to disable (not available on OpenRouter or deprecated)
MODELS_TO_DISABLE = [
    'claude-3-5-sonnet-20240620',
    'claude-3-opus-20240229',
    'claude-3-sonnet-20240229',
    'grok-3-fast',
    'grok-3-mini-fast',
]


def upgrade() -> None:
    """Fix model names to match OpenRouter API."""

    # Fix Anthropic models
    for old_name, new_name in ANTHROPIC_FIXES:
        op.execute(f"""
            UPDATE ai_models
            SET model_name = '{new_name}'
            WHERE model_name = '{old_name}'
        """)

    # Fix Google models
    for old_name, new_name in GOOGLE_FIXES:
        op.execute(f"""
            UPDATE ai_models
            SET model_name = '{new_name}'
            WHERE model_name = '{old_name}'
        """)

    # Fix xAI models
    for old_name, new_name in XAI_FIXES:
        op.execute(f"""
            UPDATE ai_models
            SET model_name = '{new_name}'
            WHERE model_name = '{old_name}'
        """)

    # Disable models not available on OpenRouter
    for model_name in MODELS_TO_DISABLE:
        op.execute(f"""
            UPDATE ai_models
            SET enabled = false
            WHERE model_name = '{model_name}'
        """)


def downgrade() -> None:
    """Revert model name changes."""

    # Revert Anthropic models
    for old_name, new_name in ANTHROPIC_FIXES:
        op.execute(f"""
            UPDATE ai_models
            SET model_name = '{old_name}'
            WHERE model_name = '{new_name}'
        """)

    # Revert Google models
    for old_name, new_name in GOOGLE_FIXES:
        op.execute(f"""
            UPDATE ai_models
            SET model_name = '{old_name}'
            WHERE model_name = '{new_name}'
        """)

    # Revert xAI models
    for old_name, new_name in XAI_FIXES:
        op.execute(f"""
            UPDATE ai_models
            SET model_name = '{old_name}'
            WHERE model_name = '{new_name}'
        """)

    # Re-enable disabled models
    for model_name in MODELS_TO_DISABLE:
        op.execute(f"""
            UPDATE ai_models
            SET enabled = true
            WHERE model_name = '{model_name}'
        """)
