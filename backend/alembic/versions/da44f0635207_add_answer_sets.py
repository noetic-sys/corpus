"""add_answer_sets

Revision ID: da44f0635207
Revises: a12a31032e6f
Create Date: 2025-08-26 17:12:51.170428

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da44f0635207'
down_revision: Union[str, Sequence[str], None] = 'a12a31032e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create answer_sets table
    op.create_table(
        'answer_sets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('matrix_cell_id', sa.BigInteger(), nullable=False),
        sa.Column('question_type_id', sa.Integer(), nullable=False),
        sa.Column('answer_found', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['matrix_cell_id'], ['matrix_cells.id']),
        sa.ForeignKeyConstraint(['question_type_id'], ['question_types.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_answer_sets_id'), 'answer_sets', ['id'])
    op.create_index(op.f('ix_answer_sets_matrix_cell_id'), 'answer_sets', ['matrix_cell_id'])

    # Create answers table
    op.create_table(
        'answers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('answer_set_id', sa.Integer(), nullable=False),
        sa.Column('answer_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['answer_set_id'], ['answer_sets.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_answers_id'), 'answers', ['id'])

    # Add current_answer_set_id to matrix_cells table
    op.add_column('matrix_cells', sa.Column('current_answer_set_id', sa.BigInteger(), nullable=True))
    op.create_index(op.f('ix_matrix_cells_current_answer_set_id'), 'matrix_cells', ['current_answer_set_id'])
    op.create_foreign_key('fk_matrix_cells_current_answer_set_id', 'matrix_cells', 'answer_sets', ['current_answer_set_id'], ['id'])

    # Drop the old current_answer_id column and related constraints
    op.drop_constraint('matrix_cells_current_answer_id_fkey', 'matrix_cells', type_='foreignkey')
    op.drop_index('ix_matrix_cells_current_answer_id', table_name='matrix_cells')
    op.drop_column('matrix_cells', 'current_answer_id')
    
    # Drop the old matrix_cell_answers table
    op.drop_index('ix_matrix_cell_answers_question_type_id', table_name='matrix_cell_answers')
    op.drop_index('ix_matrix_cell_answers_matrix_cell_id', table_name='matrix_cell_answers')
    op.drop_index('ix_matrix_cell_answers_id', table_name='matrix_cell_answers')
    op.drop_table('matrix_cell_answers')


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate the old matrix_cell_answers table
    op.create_table('matrix_cell_answers',
        sa.Column('id', sa.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('matrix_cell_id', sa.BIGINT(), nullable=False),
        sa.Column('question_type_id', sa.BIGINT(), nullable=False),
        sa.Column('answer_data', sa.JSON(), nullable=False),
        sa.Column('answer_found', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('processing_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['matrix_cell_id'], ['matrix_cells.id']),
        sa.ForeignKeyConstraint(['question_type_id'], ['question_types.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_matrix_cell_answers_id', 'matrix_cell_answers', ['id'])
    op.create_index('ix_matrix_cell_answers_matrix_cell_id', 'matrix_cell_answers', ['matrix_cell_id'])
    op.create_index('ix_matrix_cell_answers_question_type_id', 'matrix_cell_answers', ['question_type_id'])
    
    # Add back the old current_answer_id column
    op.add_column('matrix_cells', sa.Column('current_answer_id', sa.BigInteger(), nullable=True))
    op.create_index('ix_matrix_cells_current_answer_id', 'matrix_cells', ['current_answer_id'])
    op.create_foreign_key('matrix_cells_current_answer_id_fkey', 'matrix_cells', 'matrix_cell_answers', ['current_answer_id'], ['id'])

    # Drop current_answer_set_id and its constraints
    op.drop_constraint('fk_matrix_cells_current_answer_set_id', 'matrix_cells', type_='foreignkey')
    op.drop_index(op.f('ix_matrix_cells_current_answer_set_id'), table_name='matrix_cells')
    op.drop_column('matrix_cells', 'current_answer_set_id')

    # Drop answers table
    op.drop_index(op.f('ix_answers_id'), table_name='answers')
    op.drop_table('answers')

    # Drop answer_sets table
    op.drop_index(op.f('ix_answer_sets_matrix_cell_id'), table_name='answer_sets')
    op.drop_index(op.f('ix_answer_sets_id'), table_name='answer_sets')
    op.drop_table('answer_sets')
