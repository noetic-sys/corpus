"""add_lookup_indices

Revision ID: dd1e3b16f73b
Revises: 180af2f77690
Create Date: 2025-08-28 16:57:57.738666

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'dd1e3b16f73b'
down_revision: Union[str, Sequence[str], None] = '180af2f77690'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add COMPOSITE indices for improved query performance on multi-column lookups."""
    
    # Universal (id, deleted) composite indices for entities WITH deleted column
    # Critical for base repository get() operations combining ID + deleted filters
    op.create_index('ix_questions_id_deleted', 'questions', ['id', 'deleted'], unique=False)
    op.create_index('ix_matrix_documents_id_deleted', 'matrix_documents', ['id', 'deleted'], unique=False)
    op.create_index('ix_documents_id_deleted', 'documents', ['id', 'deleted'], unique=False)
    op.create_index('ix_matrices_id_deleted', 'matrices', ['id', 'deleted'], unique=False)
    op.create_index('ix_workspaces_id_deleted', 'workspaces', ['id', 'deleted'], unique=False)
    op.create_index('ix_matrix_cells_id_deleted', 'matrix_cells', ['id', 'deleted'], unique=False)
    op.create_index('ix_matrix_tpl_vars_id_del', 'matrix_template_variables', ['id', 'deleted'], unique=False)
    op.create_index('ix_q_tpl_vars_id_del', 'question_template_variables', ['id', 'deleted'], unique=False)
    
    # AI Model performance optimization - composite index for provider join + enabled filter
    # Combines provider_id and enabled for efficient filtered joins
    op.create_index('ix_ai_models_provider_enabled', 'ai_models', ['provider_id', 'enabled'], unique=False)
    
    # Matrix cell lookup patterns - multi-column queries with deleted filter
    op.create_index('ix_matrix_cells_matrix_del', 'matrix_cells', ['matrix_id', 'deleted'], unique=False)
    op.create_index('ix_matrix_cells_doc_q_del', 'matrix_cells', ['document_id', 'question_id', 'deleted'], unique=False)
    op.create_index('ix_matrix_cells_matrix_doc_del', 'matrix_cells', ['matrix_id', 'document_id', 'deleted'], unique=False)
    op.create_index('ix_matrix_cells_matrix_q_del', 'matrix_cells', ['matrix_id', 'question_id', 'deleted'], unique=False)
    op.create_index('ix_matrix_cells_matrix_doc_q_del', 'matrix_cells', ['matrix_id', 'document_id', 'question_id', 'deleted'], unique=False)
    
    # Question lookup patterns - matrix + deleted composite queries
    op.create_index('ix_questions_matrix_del', 'questions', ['matrix_id', 'deleted'], unique=False)
    
    # Matrix lookup patterns - workspace + deleted composite queries  
    op.create_index('ix_matrices_workspace_del', 'matrices', ['workspace_id', 'deleted'], unique=False)
    
    # Matrix document association patterns - multi-column + deleted queries
    op.create_index('ix_matrix_docs_matrix_del', 'matrix_documents', ['matrix_id', 'deleted'], unique=False)
    op.create_index('ix_matrix_docs_doc_del', 'matrix_documents', ['document_id', 'deleted'], unique=False)
    op.create_index('ix_matrix_docs_matrix_doc_del', 'matrix_documents', ['matrix_id', 'document_id', 'deleted'], unique=False)
    
    # Template variable junction table patterns - complex multi-column lookups
    op.create_index('ix_matrix_tpl_vars_matrix_del', 'matrix_template_variables', ['matrix_id', 'deleted'], unique=False)
    op.create_index('ix_q_tpl_vars_q_del', 'question_template_variables', ['question_id', 'deleted'], unique=False)
    op.create_index('ix_q_tpl_vars_tpl_del', 'question_template_variables', ['template_variable_id', 'deleted'], unique=False)
    op.create_index('ix_q_tpl_vars_q_tpl_del', 'question_template_variables', ['question_id', 'template_variable_id', 'deleted'], unique=False)
    
    # Job processing composite patterns - combining foreign key + status for efficient lookups
    op.create_index('ix_doc_idx_jobs_doc_status', 'document_indexing_jobs', ['document_id', 'status'], unique=False)
    op.create_index('ix_qa_jobs_cell_status', 'qa_jobs', ['matrix_cell_id', 'status'], unique=False)


def downgrade() -> None:
    """Remove the composite indices added in upgrade."""
    
    # Job processing composite indices  
    op.drop_index('ix_qa_jobs_cell_status', table_name='qa_jobs')
    op.drop_index('ix_doc_idx_jobs_doc_status', table_name='document_indexing_jobs')
    
    # Template variable composite indices
    op.drop_index('ix_q_tpl_vars_q_tpl_del', table_name='question_template_variables')
    op.drop_index('ix_q_tpl_vars_tpl_del', table_name='question_template_variables')
    op.drop_index('ix_q_tpl_vars_q_del', table_name='question_template_variables')
    op.drop_index('ix_matrix_tpl_vars_matrix_del', table_name='matrix_template_variables')
    
    # Matrix document association composite indices
    op.drop_index('ix_matrix_docs_matrix_doc_del', table_name='matrix_documents')
    op.drop_index('ix_matrix_docs_doc_del', table_name='matrix_documents')
    op.drop_index('ix_matrix_docs_matrix_del', table_name='matrix_documents')
    
    # Matrix lookup composite indices
    op.drop_index('ix_matrices_workspace_del', table_name='matrices')
    
    # Question lookup composite indices
    op.drop_index('ix_questions_matrix_del', table_name='questions')
    
    # Matrix cell lookup composite indices
    op.drop_index('ix_matrix_cells_matrix_doc_q_del', table_name='matrix_cells')
    op.drop_index('ix_matrix_cells_matrix_q_del', table_name='matrix_cells')
    op.drop_index('ix_matrix_cells_matrix_doc_del', table_name='matrix_cells')
    op.drop_index('ix_matrix_cells_doc_q_del', table_name='matrix_cells')
    op.drop_index('ix_matrix_cells_matrix_del', table_name='matrix_cells')
    
    # AI Model optimization composite index
    op.drop_index('ix_ai_models_provider_enabled', table_name='ai_models')
    
    # Universal (id, deleted) composite indices - only for tables WITH deleted column
    op.drop_index('ix_q_tpl_vars_id_del', table_name='question_template_variables')
    op.drop_index('ix_matrix_tpl_vars_id_del', table_name='matrix_template_variables')
    op.drop_index('ix_matrix_cells_id_deleted', table_name='matrix_cells')
    op.drop_index('ix_workspaces_id_deleted', table_name='workspaces')
    op.drop_index('ix_matrices_id_deleted', table_name='matrices')
    op.drop_index('ix_documents_id_deleted', table_name='documents')
    op.drop_index('ix_matrix_documents_id_deleted', table_name='matrix_documents')
    op.drop_index('ix_questions_id_deleted', table_name='questions')
