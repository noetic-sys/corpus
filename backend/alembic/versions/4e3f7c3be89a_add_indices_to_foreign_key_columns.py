"""Add indices to foreign key columns

Revision ID: 4e3f7c3be89a
Revises: e4f00ee29b19
Create Date: 2025-07-23 17:05:28.033745

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4e3f7c3be89a'
down_revision: Union[str, Sequence[str], None] = 'e4f00ee29b19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indices to foreign key columns for better query performance."""
    # Add index to documents.matrix_id
    op.create_index('ix_documents_matrix_id', 'documents', ['matrix_id'], unique=False)
    
    # Add index to questions.matrix_id  
    op.create_index('ix_questions_matrix_id', 'questions', ['matrix_id'], unique=False)
    
    # Add indices to matrix_cells foreign keys
    op.create_index('ix_matrix_cells_matrix_id', 'matrix_cells', ['matrix_id'], unique=False)
    op.create_index('ix_matrix_cells_document_id', 'matrix_cells', ['document_id'], unique=False)  
    op.create_index('ix_matrix_cells_question_id', 'matrix_cells', ['question_id'], unique=False)


def downgrade() -> None:
    """Remove the added indices."""
    # Drop the indices we added
    op.drop_index('ix_matrix_cells_question_id', table_name='matrix_cells')
    op.drop_index('ix_matrix_cells_document_id', table_name='matrix_cells')
    op.drop_index('ix_matrix_cells_matrix_id', table_name='matrix_cells')
    op.drop_index('ix_questions_matrix_id', table_name='questions')
    op.drop_index('ix_documents_matrix_id', table_name='documents')
