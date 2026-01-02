"""add_deleted_columns_to_entity_sets

Revision ID: 5b76e1a45b0a
Revises: 2deb94835e88
Create Date: 2025-10-19 00:41:39.159066

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b76e1a45b0a'
down_revision: Union[str, Sequence[str], None] = '2deb94835e88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add deleted column to matrix_entity_sets
    op.add_column('matrix_entity_sets',
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default='false'))

    # Add deleted column to matrix_entity_set_members
    op.add_column('matrix_entity_set_members',
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default='false'))

    # Add deleted column to matrix_cell_entity_refs
    op.add_column('matrix_cell_entity_refs',
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove deleted column from matrix_cell_entity_refs
    op.drop_column('matrix_cell_entity_refs', 'deleted')

    # Remove deleted column from matrix_entity_set_members
    op.drop_column('matrix_entity_set_members', 'deleted')

    # Remove deleted column from matrix_entity_sets
    op.drop_column('matrix_entity_sets', 'deleted')
