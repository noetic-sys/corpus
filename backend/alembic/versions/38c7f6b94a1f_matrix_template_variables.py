"""matrix_template_variables

Revision ID: 38c7f6b94a1f
Revises: 085b19cca784
Create Date: 2025-08-01 14:18:23.613597

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '38c7f6b94a1f'
down_revision: Union[str, Sequence[str], None] = 'a06adee7f5fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'matrix_template_variables',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('template_string', sa.Text(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('matrix_id', sa.BigInteger(), nullable=False),
        sa.Column('deleted', sa.Boolean(), nullable=False, default=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['matrix_id'], ['matrices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_matrix_template_variables_id'), 'matrix_template_variables', ['id'], unique=False)
    op.create_index(op.f('ix_matrix_template_variables_matrix_id'), 'matrix_template_variables', ['matrix_id'], unique=False)
    op.create_index(op.f('ix_matrix_template_variables_deleted'), 'matrix_template_variables', ['deleted'], unique=False)
    
    # Create junction table for question template variables
    op.create_table(
        'question_template_variables',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('question_id', sa.BigInteger(), nullable=False),
        sa.Column('template_variable_id', sa.BigInteger(), nullable=False),
        sa.Column('deleted', sa.Boolean(), nullable=False, default=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
        sa.ForeignKeyConstraint(['template_variable_id'], ['matrix_template_variables.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_question_template_variables_id'), 'question_template_variables', ['id'], unique=False)
    op.create_index(op.f('ix_question_template_variables_question_id'), 'question_template_variables', ['question_id'], unique=False)
    op.create_index(op.f('ix_question_template_variables_template_variable_id'), 'question_template_variables', ['template_variable_id'], unique=False)
    op.create_index(op.f('ix_question_template_variables_deleted'), 'question_template_variables', ['deleted'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop junction table first (has foreign keys)
    op.drop_index(op.f('ix_question_template_variables_deleted'), table_name='question_template_variables')
    op.drop_index(op.f('ix_question_template_variables_template_variable_id'), table_name='question_template_variables')
    op.drop_index(op.f('ix_question_template_variables_question_id'), table_name='question_template_variables')
    op.drop_index(op.f('ix_question_template_variables_id'), table_name='question_template_variables')
    op.drop_table('question_template_variables')
    
    # Drop main table
    op.drop_index(op.f('ix_matrix_template_variables_deleted'), table_name='matrix_template_variables')
    op.drop_index(op.f('ix_matrix_template_variables_matrix_id'), table_name='matrix_template_variables')
    op.drop_index(op.f('ix_matrix_template_variables_id'), table_name='matrix_template_variables')
    op.drop_table('matrix_template_variables')
