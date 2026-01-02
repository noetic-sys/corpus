"""add_company_indexing_columns

Revision ID: 5f2eea6c488e
Revises: 937a7f8179e0
Create Date: 2025-09-10 11:42:37.669265

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5f2eea6c488e'
down_revision: Union[str, Sequence[str], None] = '937a7f8179e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add company-based composite indices for improved multi-tenant query performance."""
    
    # High Priority - Core Entity Lookups with Company Filtering
    op.create_index('ix_workspaces_company_deleted', 'workspaces', ['company_id', 'deleted'])
    op.create_index('ix_matrices_company_deleted', 'matrices', ['company_id', 'deleted'])  
    op.create_index('ix_matrix_cells_company_deleted', 'matrix_cells', ['company_id', 'deleted'])
    op.create_index('ix_documents_company_deleted', 'documents', ['company_id', 'deleted'])
    op.create_index('ix_questions_company_deleted', 'questions', ['company_id', 'deleted'])

    # Medium Priority - Specific Use Cases
    op.create_index('ix_conversations_company_active_deleted', 'conversations', ['company_id', 'is_active', 'deleted'])
    op.create_index('ix_messages_conversation_company', 'messages', ['conversation_id', 'company_id'])
    op.create_index('ix_documents_storage_key_company', 'documents', ['storage_key', 'company_id'])
    op.create_index('ix_documents_checksum_company', 'documents', ['checksum', 'company_id'])
    op.create_index('ix_questions_matrix_company_deleted', 'questions', ['matrix_id', 'company_id', 'deleted'])
    
    # Matrix Template Variables - Company-based lookups
    op.create_index('ix_matrix_tpl_vars_company_deleted', 'matrix_template_variables', ['company_id', 'deleted'])
    op.create_index('ix_matrix_tpl_vars_matrix_company_deleted', 'matrix_template_variables', ['matrix_id', 'company_id', 'deleted'])
    op.create_index('ix_matrix_tpl_vars_matrix_string_company', 'matrix_template_variables', ['matrix_id', 'template_string', 'company_id'])
    
    # Question Template Variables - Company-based lookups
    op.create_index('ix_question_tpl_vars_company_deleted', 'question_template_variables', ['company_id', 'deleted'])
    op.create_index('ix_question_tpl_vars_question_company_deleted', 'question_template_variables', ['question_id', 'company_id', 'deleted'])
    op.create_index('ix_question_tpl_vars_template_company_deleted', 'question_template_variables', ['template_variable_id', 'company_id', 'deleted'])

    # Answer Sets - Company-based lookups
    op.create_index('ix_answer_sets_company', 'answer_sets', ['company_id'])
    op.create_index('ix_answer_sets_matrix_cell_company', 'answer_sets', ['matrix_cell_id', 'company_id'])
    op.create_index('ix_answer_sets_matrix_cell_company_created', 'answer_sets', ['matrix_cell_id', 'company_id', 'created_at'])

    # Answers - Company-based lookups
    op.create_index('ix_answers_company', 'answers', ['company_id'])
    op.create_index('ix_answers_answer_set_company', 'answers', ['answer_set_id', 'company_id'])
    op.create_index('ix_answers_answer_set_company_created', 'answers', ['answer_set_id', 'company_id', 'created_at'])

    # Citation Sets - Company-based lookups
    op.create_index('ix_citation_sets_company', 'citation_sets', ['company_id'])
    op.create_index('ix_citation_sets_answer_company', 'citation_sets', ['answer_id', 'company_id'])
    op.create_index('ix_citation_sets_answer_company_created', 'citation_sets', ['answer_id', 'company_id', 'created_at'])

    # Citations - Company-based lookups
    op.create_index('ix_citations_company', 'citations', ['company_id'])
    op.create_index('ix_citations_citation_set_company', 'citations', ['citation_set_id', 'company_id'])
    op.create_index('ix_citations_document_company', 'citations', ['document_id', 'company_id'])
    op.create_index('ix_citations_citation_set_company_order', 'citations', ['citation_set_id', 'company_id', 'citation_order'])

    # Lower Priority - Less Frequent Patterns  
    op.create_index('ix_messages_tool_call_company', 'messages', ['tool_call_id', 'company_id'])
    op.create_index('ix_documents_extraction_status_company', 'documents', ['extraction_status', 'company_id'])


def downgrade() -> None:
    """Remove company-based composite indices."""
    
    # Remove in reverse order
    op.drop_index('ix_documents_extraction_status_company', 'documents')
    op.drop_index('ix_messages_tool_call_company', 'messages')
    
    # Citations - Company-based lookups
    op.drop_index('ix_citations_citation_set_company_order', 'citations')
    op.drop_index('ix_citations_document_company', 'citations')
    op.drop_index('ix_citations_citation_set_company', 'citations')
    op.drop_index('ix_citations_company', 'citations')
    
    # Citation Sets - Company-based lookups
    op.drop_index('ix_citation_sets_answer_company_created', 'citation_sets')
    op.drop_index('ix_citation_sets_answer_company', 'citation_sets')
    op.drop_index('ix_citation_sets_company', 'citation_sets')
    
    # Answers - Company-based lookups
    op.drop_index('ix_answers_answer_set_company_created', 'answers')
    op.drop_index('ix_answers_answer_set_company', 'answers')
    op.drop_index('ix_answers_company', 'answers')
    
    # Answer Sets - Company-based lookups
    op.drop_index('ix_answer_sets_matrix_cell_company_created', 'answer_sets')
    op.drop_index('ix_answer_sets_matrix_cell_company', 'answer_sets')
    op.drop_index('ix_answer_sets_company', 'answer_sets')
    
    # Question Template Variables - Company-based lookups
    op.drop_index('ix_question_tpl_vars_template_company_deleted', 'question_template_variables')
    op.drop_index('ix_question_tpl_vars_question_company_deleted', 'question_template_variables')
    op.drop_index('ix_question_tpl_vars_company_deleted', 'question_template_variables')
    
    # Matrix Template Variables - Company-based lookups
    op.drop_index('ix_matrix_tpl_vars_matrix_string_company', 'matrix_template_variables')
    op.drop_index('ix_matrix_tpl_vars_matrix_company_deleted', 'matrix_template_variables')
    op.drop_index('ix_matrix_tpl_vars_company_deleted', 'matrix_template_variables')
    
    op.drop_index('ix_questions_matrix_company_deleted', 'questions')
    op.drop_index('ix_documents_checksum_company', 'documents')
    op.drop_index('ix_documents_storage_key_company', 'documents')
    op.drop_index('ix_messages_conversation_company', 'messages')
    op.drop_index('ix_conversations_company_active_deleted', 'conversations')
    
    op.drop_index('ix_questions_company_deleted', 'questions')
    op.drop_index('ix_documents_company_deleted', 'documents')
    op.drop_index('ix_matrix_cells_company_deleted', 'matrix_cells')
    op.drop_index('ix_matrices_company_deleted', 'matrices')
    op.drop_index('ix_workspaces_company_deleted', 'workspaces')
