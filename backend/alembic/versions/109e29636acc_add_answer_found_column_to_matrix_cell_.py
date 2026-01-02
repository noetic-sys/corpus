"""add_answer_found_column_to_matrix_cell_answers

Revision ID: 109e29636acc
Revises: e51997d01eb8
Create Date: 2025-07-28 18:22:03.926509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '109e29636acc'
down_revision: Union[str, Sequence[str], None] = 'e51997d01eb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add answer_found column to matrix_cell_answers table
    op.add_column('matrix_cell_answers', sa.Column('answer_found', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove answer_found column from matrix_cell_answers table
    op.drop_column('matrix_cell_answers', 'answer_found')
