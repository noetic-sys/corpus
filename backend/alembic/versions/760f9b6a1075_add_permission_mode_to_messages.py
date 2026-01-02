"""add_permission_mode_to_messages

Revision ID: 760f9b6a1075
Revises: 1b25c6e3f0ca
Create Date: 2025-10-28 17:03:17.189493

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '760f9b6a1075'
down_revision: Union[str, Sequence[str], None] = '1b25c6e3f0ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add permission_mode column to messages table
    op.add_column(
        'messages',
        sa.Column('permission_mode', sa.String(length=20), nullable=False, server_default='read')
    )
    # Add index on permission_mode
    op.create_index(op.f('ix_messages_permission_mode'), 'messages', ['permission_mode'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index on permission_mode
    op.drop_index(op.f('ix_messages_permission_mode'), table_name='messages')
    # Drop permission_mode column
    op.drop_column('messages', 'permission_mode')
