"""add_confidence_to_answer_sets

Revision ID: 2fd5369a5190
Revises: 19e88dea816b
Create Date: 2025-10-31 12:51:04.671222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2fd5369a5190'
down_revision: Union[str, Sequence[str], None] = '19e88dea816b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add confidence column to answer_sets table
    op.add_column(
        'answer_sets',
        sa.Column('confidence', sa.Float, nullable=True, server_default='1.0')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove confidence column from answer_sets table
    op.drop_column('answer_sets', 'confidence')
