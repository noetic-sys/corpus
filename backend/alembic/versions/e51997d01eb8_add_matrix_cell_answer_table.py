"""add_matrix_cell_answer_table

Revision ID: e51997d01eb8
Revises: dadb883abe01
Create Date: 2025-07-28 10:48:30.867752

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e51997d01eb8'
down_revision: Union[str, Sequence[str], None] = 'dadb883abe01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add matrix_cell_answers table and update matrix_cells."""
    # Create matrix_cell_answers table
    op.create_table('matrix_cell_answers',
        sa.Column('id', sa.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('matrix_cell_id', sa.BIGINT(), nullable=False),
        sa.Column('question_type_id', sa.BIGINT(), nullable=False),
        sa.Column('answer_data', sa.JSON(), nullable=False),
        sa.Column('processing_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['matrix_cell_id'], ['matrix_cells.id']),
        sa.ForeignKeyConstraint(['question_type_id'], ['question_types.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_matrix_cell_answers_id'), 'matrix_cell_answers', ['id'], unique=False)
    op.create_index(op.f('ix_matrix_cell_answers_matrix_cell_id'), 'matrix_cell_answers', ['matrix_cell_id'], unique=False)
    op.create_index(op.f('ix_matrix_cell_answers_question_type_id'), 'matrix_cell_answers', ['question_type_id'], unique=False)
    
    # Add current_answer_id column to matrix_cells table
    op.add_column('matrix_cells', sa.Column('current_answer_id', sa.BIGINT(), nullable=True))
    op.create_index(op.f('ix_matrix_cells_current_answer_id'), 'matrix_cells', ['current_answer_id'], unique=False)
    op.create_foreign_key(op.f('matrix_cells_current_answer_id_fkey'), 'matrix_cells', 'matrix_cell_answers', ['current_answer_id'], ['id'])
    
    # Remove the old answer column from matrix_cells
    op.drop_column('matrix_cells', 'answer')


def downgrade() -> None:
    """Remove matrix_cell_answers table and revert matrix_cells changes."""
    # Add back the answer column to matrix_cells
    op.add_column('matrix_cells', sa.Column('answer', sa.TEXT(), nullable=True))
    
    # Remove foreign key and index for current_answer_id
    op.drop_constraint(op.f('matrix_cells_current_answer_id_fkey'), 'matrix_cells', type_='foreignkey')
    op.drop_index(op.f('ix_matrix_cells_current_answer_id'), table_name='matrix_cells')
    op.drop_column('matrix_cells', 'current_answer_id')
    
    # Drop matrix_cell_answers table
    op.drop_index(op.f('ix_matrix_cell_answers_question_type_id'), table_name='matrix_cell_answers')
    op.drop_index(op.f('ix_matrix_cell_answers_matrix_cell_id'), table_name='matrix_cell_answers')
    op.drop_index(op.f('ix_matrix_cell_answers_id'), table_name='matrix_cell_answers')
    op.drop_table('matrix_cell_answers')