"""add_label_to_entity_set_members

Revision ID: 2deb94835e88
Revises: 5dfa69679e3f
Create Date: 2025-10-16 15:53:17.241334

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2deb94835e88'
down_revision: Union[str, Sequence[str], None] = '5dfa69679e3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add nullable label column to entity set members
    op.add_column('matrix_entity_set_members', sa.Column('label', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove label column
    op.drop_column('matrix_entity_set_members', 'label')
