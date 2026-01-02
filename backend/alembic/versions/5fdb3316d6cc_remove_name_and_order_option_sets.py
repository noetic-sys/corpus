"""remove_name_and_order_option_sets

Revision ID: 5fdb3316d6cc
Revises: 109e29636acc
Create Date: 2025-07-29 00:45:48.032918

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5fdb3316d6cc'
down_revision: Union[str, Sequence[str], None] = '109e29636acc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove name column from question_option_sets
    op.drop_column('question_option_sets', 'name')
    
    # Remove display_order column from question_options
    op.drop_column('question_options', 'display_order')


def downgrade() -> None:
    """Downgrade schema."""
    # Add back display_order column to question_options
    op.add_column('question_options', sa.Column('display_order', sa.INTEGER(), nullable=False, server_default='0'))
    
    # Add back name column to question_option_sets  
    op.add_column('question_option_sets', sa.Column('name', sa.String(), nullable=True))
