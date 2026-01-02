"""add_gemini_models

Revision ID: 82f7d53090e6
Revises: 14802c835b3a
Create Date: 2025-08-04 13:25:49.569456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '82f7d53090e6'
down_revision: Union[str, Sequence[str], None] = '14802c835b3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Insert Google provider with explicit ID
    providers_table = sa.table('ai_providers',
        sa.column('id', sa.BigInteger),
        sa.column('name', sa.String),
        sa.column('display_name', sa.String),
        sa.column('enabled', sa.Boolean)
    )
    
    op.bulk_insert(providers_table, [
        {'id': 3, 'name': 'google', 'display_name': 'Google', 'enabled': True}
    ])
    
    # Insert Gemini models with explicit provider_id = 3
    models_table = sa.table('ai_models',
        sa.column('provider_id', sa.BigInteger),
        sa.column('model_name', sa.String),
        sa.column('display_name', sa.String),
        sa.column('default_temperature', sa.Float),
        sa.column('default_max_tokens', sa.Integer),
        sa.column('enabled', sa.Boolean)
    )
    
    op.bulk_insert(models_table, [
        {'provider_id': 3, 'model_name': 'gemini-2.5-pro', 'display_name': 'Gemini 2.5 Pro', 'default_temperature': 0.7, 'default_max_tokens': None, 'enabled': True},
        {'provider_id': 3, 'model_name': 'gemini-2.5-flash', 'display_name': 'Gemini 2.5 Flash', 'default_temperature': 0.7, 'default_max_tokens': None, 'enabled': True},
        {'provider_id': 3, 'model_name': 'gemini-2.5-flash-lite', 'display_name': 'Gemini 2.5 Flash-Lite', 'default_temperature': 0.7, 'default_max_tokens': None, 'enabled': True}
    ])

def downgrade() -> None:
    """Downgrade schema."""
    # Remove Gemini models
    op.execute("DELETE FROM ai_models WHERE provider_id = 3")
    
    # Remove Google provider
    op.execute("DELETE FROM ai_providers WHERE id = 3")
