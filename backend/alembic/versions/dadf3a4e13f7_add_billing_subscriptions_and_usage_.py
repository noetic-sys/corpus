"""add_billing_subscriptions_and_usage_events

Revision ID: dadf3a4e13f7
Revises: 63166e6acb4b
Create Date: 2025-11-13 13:23:31.736994

Adds billing infrastructure for subscription management and usage tracking.

Tables:
- subscriptions: Stores company subscription tier, status, and external platform IDs (Lago/Stripe)
- usage_events: Audit trail for all billable actions (questions, document uploads, etc.)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'dadf3a4e13f7'
down_revision: Union[str, Sequence[str], None] = '63166e6acb4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add billing tables with proper indexes and constraints."""

    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('company_id', sa.BigInteger(), nullable=False),

        # Subscription details
        sa.Column('tier', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),

        # External platform IDs (nullable until connected)
        sa.Column('lago_customer_id', sa.String(255), nullable=True),
        sa.Column('lago_subscription_id', sa.String(255), nullable=True),
        # Note: stripe_customer_id lives on companies table (represents company identity)
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),

        # Payment provider
        sa.Column('payment_provider', sa.String(50), nullable=False, server_default='stripe'),

        # Billing cycle dates
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=False),

        # Lifecycle timestamps
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('suspended_at', sa.DateTime(timezone=True), nullable=True),

        # Standard timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    )

    # Indexes for subscriptions table
    op.create_index('idx_subscriptions_company_id', 'subscriptions', ['company_id'], unique=True)
    op.create_index('idx_subscriptions_tier', 'subscriptions', ['tier'])
    op.create_index('idx_subscriptions_status', 'subscriptions', ['status'])
    op.create_index('idx_subscriptions_status_tier', 'subscriptions', ['status', 'tier'])
    op.create_index('idx_subscriptions_period_end', 'subscriptions', ['current_period_end'])
    op.create_index('idx_subscriptions_lago_customer_id', 'subscriptions', ['lago_customer_id'], unique=True, postgresql_where=sa.text('lago_customer_id IS NOT NULL'))
    op.create_index('idx_subscriptions_lago_subscription_id', 'subscriptions', ['lago_subscription_id'], unique=True, postgresql_where=sa.text('lago_subscription_id IS NOT NULL'))
    op.create_index('idx_subscriptions_stripe_subscription_id', 'subscriptions', ['stripe_subscription_id'], unique=True, postgresql_where=sa.text('stripe_subscription_id IS NOT NULL'))

    # Add stripe_customer_id to companies table (represents company identity, not subscription)
    op.add_column('companies', sa.Column('stripe_customer_id', sa.String(255), nullable=True))
    op.create_index('ix_companies_stripe_customer_id', 'companies', ['stripe_customer_id'], unique=True)

    # Create usage_events table (high volume, optimized for writes)
    op.create_table(
        'usage_events',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('company_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),

        # Event details
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),

        # Lago tracking IDs for correlation
        sa.Column('lago_transaction_id', sa.String(255), nullable=True),
        sa.Column('lago_event_id', sa.String(255), nullable=True),

        # Timestamp (partition key for future partitioning)
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )

    # Indexes for usage_events table (optimized for analytics queries)
    op.create_index('idx_usage_events_company_id', 'usage_events', ['company_id'])
    op.create_index('idx_usage_events_user_id', 'usage_events', ['user_id'])
    op.create_index('idx_usage_events_event_type', 'usage_events', ['event_type'])
    op.create_index('idx_usage_events_created_at', 'usage_events', ['created_at'])
    op.create_index('idx_usage_events_company_type_date', 'usage_events', ['company_id', 'event_type', 'created_at'])
    op.create_index('idx_usage_events_user_date', 'usage_events', ['user_id', 'created_at'])
    op.create_index('idx_usage_events_lago_transaction', 'usage_events', ['lago_transaction_id'], unique=True, postgresql_where=sa.text('lago_transaction_id IS NOT NULL'))

    # Add BRIN index on created_at for efficient time-range queries on large table
    op.execute('CREATE INDEX idx_usage_events_created_at_brin ON usage_events USING BRIN (created_at)')


def downgrade() -> None:
    """Remove billing tables."""
    op.drop_table('usage_events')
    op.drop_table('subscriptions')
    op.drop_index('ix_companies_stripe_customer_id', table_name='companies')
    op.drop_column('companies', 'stripe_customer_id')
