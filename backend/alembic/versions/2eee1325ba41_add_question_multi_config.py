"""add_question_multi_config

Revision ID: 2eee1325ba41
Revises: 780989e7ddc5
Create Date: 2025-08-26 17:16:40.829760

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = '2eee1325ba41'
down_revision: Union[str, Sequence[str], None] = '780989e7ddc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add min_answers (non-nullable with default) and max_answers (nullable) columns
    op.add_column('questions', sa.Column('min_answers', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('questions', sa.Column('max_answers', sa.Integer(), nullable=True))
    
    # Set max_answers to 1 for existing questions for backwards compatibility
    op.execute("UPDATE questions SET max_answers = 1")


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the columns
    op.drop_column('questions', 'max_answers')
    op.drop_column('questions', 'min_answers')
