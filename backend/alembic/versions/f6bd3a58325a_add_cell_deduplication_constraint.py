"""add_cell_deduplication_constraint

Revision ID: f6bd3a58325a
Revises: 760f9b6a1075
Create Date: 2025-11-03 15:52:40.642655

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6bd3a58325a'
down_revision: Union[str, Sequence[str], None] = '760f9b6a1075'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cell signature column and unique constraint to prevent duplicate cells.

    The cell_signature is a hash of the sorted entity refs, ensuring that cells
    with identical entity combinations cannot be inserted.

    Application MUST compute and provide this value on insert.
    """

    # Add cell_signature column as non-nullable, NO DEFAULT
    # Application must compute and provide this value
    op.add_column('matrix_cells',
        sa.Column('cell_signature', sa.String(), nullable=False)
    )

    # Add unique constraint on (matrix_id, cell_signature) ONLY for non-deleted cells
    # Using partial index to only enforce uniqueness on non-deleted rows
    op.create_index(
        'idx_unique_cell_signature',
        'matrix_cells',
        ['matrix_id', 'cell_signature'],
        unique=True,
        postgresql_where=sa.text('deleted = false')
    )


def downgrade() -> None:
    """Remove cell deduplication constraint and column."""
    op.drop_index('idx_unique_cell_signature', table_name='matrix_cells')
    op.drop_column('matrix_cells', 'cell_signature')
