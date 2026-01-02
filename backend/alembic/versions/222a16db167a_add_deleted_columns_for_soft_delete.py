"""add_deleted_columns_for_soft_delete

Revision ID: 222a16db167a
Revises: 5fdb3316d6cc
Create Date: 2025-07-29 13:56:40.023653

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '222a16db167a'
down_revision: Union[str, Sequence[str], None] = '5fdb3316d6cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add deleted columns for soft delete functionality
    
    # Add deleted column to matrices table
    op.add_column('matrices', sa.Column('deleted', sa.Boolean(), nullable=False, default=False, server_default='false'))
    op.create_index(op.f('ix_matrices_deleted'), 'matrices', ['deleted'], unique=False)
    
    # Add deleted column to documents table
    op.add_column('documents', sa.Column('deleted', sa.Boolean(), nullable=False, default=False, server_default='false'))
    op.create_index(op.f('ix_documents_deleted'), 'documents', ['deleted'], unique=False)
    
    # Add deleted column to questions table
    op.add_column('questions', sa.Column('deleted', sa.Boolean(), nullable=False, default=False, server_default='false'))
    op.create_index(op.f('ix_questions_deleted'), 'questions', ['deleted'], unique=False)
    
    # Add deleted column to matrix_cells table
    op.add_column('matrix_cells', sa.Column('deleted', sa.Boolean(), nullable=False, default=False, server_default='false'))
    op.create_index(op.f('ix_matrix_cells_deleted'), 'matrix_cells', ['deleted'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove deleted columns and indexes
    
    # Remove deleted column from matrix_cells table
    op.drop_index(op.f('ix_matrix_cells_deleted'), table_name='matrix_cells')
    op.drop_column('matrix_cells', 'deleted')
    
    # Remove deleted column from questions table
    op.drop_index(op.f('ix_questions_deleted'), table_name='questions')
    op.drop_column('questions', 'deleted')
    
    # Remove deleted column from documents table
    op.drop_index(op.f('ix_documents_deleted'), table_name='documents')
    op.drop_column('documents', 'deleted')
    
    # Remove deleted column from matrices table
    op.drop_index(op.f('ix_matrices_deleted'), table_name='matrices')
    op.drop_column('matrices', 'deleted')
