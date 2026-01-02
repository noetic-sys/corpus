"""add_grok_models

Revision ID: 00b46a442b7a
Revises: 82f7d53090e6
Create Date: 2025-08-04 13:26:46.846569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '00b46a442b7a'
down_revision: Union[str, Sequence[str], None] = '82f7d53090e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Insert xAI provider with explicit ID
    providers_table = sa.table('ai_providers',
        sa.column('id', sa.BigInteger),
        sa.column('name', sa.String),
        sa.column('display_name', sa.String),
        sa.column('enabled', sa.Boolean)
    )
    
    op.bulk_insert(providers_table, [
        {'id': 4, 'name': 'xai', 'display_name': 'xAI', 'enabled': True}
    ])
    
    # Insert Grok models with explicit provider_id = 4
    models_table = sa.table('ai_models',
        sa.column('provider_id', sa.BigInteger),
        sa.column('model_name', sa.String),
        sa.column('display_name', sa.String),
        sa.column('default_temperature', sa.Float),
        sa.column('default_max_tokens', sa.Integer),
        sa.column('enabled', sa.Boolean)
    )
    
    op.bulk_insert(models_table, [
        {'provider_id': 4, 'model_name': 'grok-3', 'display_name': 'Grok 3', 'default_temperature': 0.7, 'default_max_tokens': None, 'enabled': True},
        {'provider_id': 4, 'model_name': 'grok-3-mini', 'display_name': 'Grok 3 Mini', 'default_temperature': 0.7, 'default_max_tokens': None, 'enabled': True},
        {'provider_id': 4, 'model_name': 'grok-4', 'display_name': 'Grok 4', 'default_temperature': 0.7, 'default_max_tokens': None, 'enabled': True}
    ])

def downgrade() -> None:
    """Downgrade schema."""
    # Remove Grok models
    op.execute("DELETE FROM ai_models WHERE provider_id = 4")
    
    # Remove xAI provider
    op.execute("DELETE FROM ai_providers WHERE id = 4")
