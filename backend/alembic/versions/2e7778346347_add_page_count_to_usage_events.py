"""add_file_size_bytes_to_usage_events

Revision ID: 2e7778346347
Revises: dadf3a4e13f7
Create Date: 2025-11-21 13:22:58.893659

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e7778346347'
down_revision: Union[str, Sequence[str], None] = 'dadf3a4e13f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add file_size_bytes column to usage_events table
    op.add_column(
        'usage_events',
        sa.Column('file_size_bytes', sa.Integer(), nullable=True)
    )

    # Create index on file_size_bytes for fast aggregation queries
    op.create_index(
        'ix_usage_events_file_size_bytes',
        'usage_events',
        ['file_size_bytes'],
        unique=False
    )

    # Add quantity column for batched usage tracking
    op.add_column(
        'usage_events',
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1')
    )

    # Remove legacy Lago columns (no longer used)
    op.drop_index('idx_usage_events_lago_transaction', table_name='usage_events')
    op.drop_column('usage_events', 'lago_transaction_id')
    op.drop_column('usage_events', 'lago_event_id')


def downgrade() -> None:
    """Downgrade schema."""
    # Re-add Lago columns
    op.add_column(
        'usage_events',
        sa.Column('lago_event_id', sa.String(255), nullable=True)
    )
    op.add_column(
        'usage_events',
        sa.Column('lago_transaction_id', sa.String(255), nullable=True)
    )
    op.create_index('idx_usage_events_lago_transaction', 'usage_events', ['lago_transaction_id'])

    # Drop quantity column
    op.drop_column('usage_events', 'quantity')

    # Drop index first
    op.drop_index('ix_usage_events_file_size_bytes', table_name='usage_events')

    # Drop file_size_bytes column
    op.drop_column('usage_events', 'file_size_bytes')
