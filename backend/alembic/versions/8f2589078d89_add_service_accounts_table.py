"""add_service_accounts_table

Revision ID: 8f2589078d89
Revises: 5b76e1a45b0a
Create Date: 2025-10-21 17:47:59.889925

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8f2589078d89'
down_revision: Union[str, Sequence[str], None] = '5b76e1a45b0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create service_accounts table."""
    op.create_table('service_accounts',
        sa.Column('id', sa.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('company_id', sa.BIGINT(), nullable=False),
        sa.Column('api_key_hash', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_service_accounts_api_key_hash'), 'service_accounts', ['api_key_hash'], unique=True)
    op.create_index(op.f('ix_service_accounts_company_id'), 'service_accounts', ['company_id'], unique=False)
    op.create_index(op.f('ix_service_accounts_deleted'), 'service_accounts', ['deleted'], unique=False)
    op.create_index(op.f('ix_service_accounts_id'), 'service_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_service_accounts_name'), 'service_accounts', ['name'], unique=False)


def downgrade() -> None:
    """Drop service_accounts table."""
    op.drop_index(op.f('ix_service_accounts_name'), table_name='service_accounts')
    op.drop_index(op.f('ix_service_accounts_id'), table_name='service_accounts')
    op.drop_index(op.f('ix_service_accounts_deleted'), table_name='service_accounts')
    op.drop_index(op.f('ix_service_accounts_company_id'), table_name='service_accounts')
    op.drop_index(op.f('ix_service_accounts_api_key_hash'), table_name='service_accounts')
    op.drop_table('service_accounts')
