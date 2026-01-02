"""remove_lago_columns_from_subscriptions

Revision ID: 5bd5e08b35df
Revises: 2e7778346347
Create Date: 2025-12-31 19:36:59.020595

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5bd5e08b35df'
down_revision: Union[str, Sequence[str], None] = '2e7778346347'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove unused Lago columns from subscriptions table."""
    # Drop indexes first
    op.drop_index('idx_subscriptions_lago_customer_id', table_name='subscriptions')
    op.drop_index('idx_subscriptions_lago_subscription_id', table_name='subscriptions')

    # Drop columns
    op.drop_column('subscriptions', 'lago_customer_id')
    op.drop_column('subscriptions', 'lago_subscription_id')


def downgrade() -> None:
    """Re-add Lago columns if needed."""
    op.add_column(
        'subscriptions',
        sa.Column('lago_customer_id', sa.String(255), nullable=True)
    )
    op.add_column(
        'subscriptions',
        sa.Column('lago_subscription_id', sa.String(255), nullable=True)
    )
    op.create_index(
        'idx_subscriptions_lago_customer_id',
        'subscriptions',
        ['lago_customer_id'],
        unique=True,
        postgresql_where=sa.text('lago_customer_id IS NOT NULL')
    )
    op.create_index(
        'idx_subscriptions_lago_subscription_id',
        'subscriptions',
        ['lago_subscription_id'],
        unique=True,
        postgresql_where=sa.text('lago_subscription_id IS NOT NULL')
    )
