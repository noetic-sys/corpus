"""add_company_id

Revision ID: a40cb53a0189
Revises: 6b8f38f6defb
Create Date: 2025-09-08 20:53:27.111419

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a40cb53a0189'
down_revision: Union[str, Sequence[str], None] = '6b8f38f6defb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add company_id to documents table
    op.add_column('documents', sa.Column('company_id', sa.BigInteger(), nullable=False, index=True))
    op.create_foreign_key('fk_documents_company', 'documents', 'companies', ['company_id'], ['id'])

    # Add company_id to workspaces table
    op.add_column('workspaces', sa.Column('company_id', sa.BigInteger(), nullable=False, index=True))
    op.create_foreign_key('fk_workspaces_company', 'workspaces', 'companies', ['company_id'], ['id'])

    # Add company_id to matrix_documents table
    op.add_column('matrix_documents', sa.Column('company_id', sa.BigInteger(), nullable=False, index=True))
    op.create_foreign_key('fk_matrix_documents_company', 'matrix_documents', 'companies', ['company_id'], ['id'])

    # Add company_id to questions table
    op.add_column('questions', sa.Column('company_id', sa.BigInteger(), nullable=False, index=True))
    op.create_foreign_key('fk_questions_company', 'questions', 'companies', ['company_id'], ['id'])

    # Add company_id to matrices table
    op.add_column('matrices', sa.Column('company_id', sa.BigInteger(), nullable=False, index=True))
    op.create_foreign_key('fk_matrices_company', 'matrices', 'companies', ['company_id'], ['id'])
    
    # Add company_id to matrix_cells table
    op.add_column('matrix_cells', sa.Column('company_id', sa.BigInteger(), nullable=False, index=True))
    op.create_foreign_key('fk_matrix_cells_company', 'matrix_cells', 'companies', ['company_id'], ['id'])
    
    # Add company_id to matrix_template_variables table
    op.add_column('matrix_template_variables', sa.Column('company_id', sa.BigInteger(), nullable=False, index=True))
    op.create_foreign_key('fk_matrix_template_variables_company', 'matrix_template_variables', 'companies', ['company_id'], ['id'])
    
    # Add company_id to question_template_variables table
    op.add_column('question_template_variables', sa.Column('company_id', sa.BigInteger(), nullable=False, index=True))
    op.create_foreign_key('fk_question_template_variables_company', 'question_template_variables', 'companies', ['company_id'], ['id'])
    
    # Add company_id to answers table
    op.add_column('answers', sa.Column('company_id', sa.BigInteger(), nullable=False, index=True))
    op.create_foreign_key('fk_answers_company', 'answers', 'companies', ['company_id'], ['id'])
    
    # Add company_id to answer_sets table
    op.add_column('answer_sets', sa.Column('company_id', sa.BigInteger(), nullable=False, index=True))
    op.create_foreign_key('fk_answer_sets_company', 'answer_sets', 'companies', ['company_id'], ['id'])
    
    # Add company_id to citations table
    op.add_column('citations', sa.Column('company_id', sa.BigInteger(), nullable=False, index=True))
    op.create_foreign_key('fk_citations_company', 'citations', 'companies', ['company_id'], ['id'])
    
    # Add company_id to citation_sets table
    op.add_column('citation_sets', sa.Column('company_id', sa.BigInteger(), nullable=False, index=True))
    op.create_foreign_key('fk_citation_sets_company', 'citation_sets', 'companies', ['company_id'], ['id'])
    
    # Add company_id to conversations table
    op.add_column('conversations', sa.Column('company_id', sa.BigInteger(), nullable=False, index=True))
    op.create_foreign_key('fk_conversations_company', 'conversations', 'companies', ['company_id'], ['id'])
    
    # Add company_id to messages table
    op.add_column('messages', sa.Column('company_id', sa.BigInteger(), nullable=False, index=True))
    op.create_foreign_key('fk_messages_company', 'messages', 'companies', ['company_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove company_id from messages table
    op.drop_constraint('fk_documents_company', 'documents', type_='foreignkey')
    op.drop_column('documents', 'company_id')
    
    # Remove company_id from workspaces table
    op.drop_constraint('fk_workspaces_company', 'workspaces', type_='foreignkey')
    op.drop_column('workspaces', 'company_id')

    ## Remove company_id from matrix_documents table
    op.drop_constraint('fk_matrix_documents_company', 'matrix_documents', type_='foreignkey')
    op.drop_column('matrix_documents', 'company_id')

    ## Remove company_id from questions table
    op.drop_constraint('fk_questions_company', 'questions', type_='foreignkey')
    op.drop_column('questions', 'company_id')

    ## Remove company_id from conversations table
    op.drop_constraint('fk_conversations_company', 'conversations', type_='foreignkey')
    op.drop_column('conversations', 'company_id')
    
    ## Remove company_id from messages table
    op.drop_constraint('fk_messages_company', 'messages', type_='foreignkey')
    op.drop_column('messages', 'company_id')

    ## Remove company_id from citation_sets table
    op.drop_constraint('fk_citation_sets_company', 'citation_sets', type_='foreignkey')
    op.drop_column('citation_sets', 'company_id')
    
    ## Remove company_id from citations table
    op.drop_constraint('fk_citations_company', 'citations', type_='foreignkey')
    op.drop_column('citations', 'company_id')
    #
    ## Remove company_id from answer_sets table
    op.drop_constraint('fk_answer_sets_company', 'answer_sets', type_='foreignkey')
    op.drop_column('answer_sets', 'company_id')
    
    ## Remove company_id from answers table
    op.drop_constraint('fk_answers_company', 'answers', type_='foreignkey')
    op.drop_column('answers', 'company_id')
    #
    ## Remove company_id from question_template_variables table
    op.drop_constraint('fk_question_template_variables_company', 'question_template_variables', type_='foreignkey')
    op.drop_column('question_template_variables', 'company_id')
    #
    ## Remove company_id from questions table
    #op.drop_constraint(None, 'questions', type_='foreignkey')
    #op.drop_column('questions', 'company_id')
    #
    ## Remove company_id from matrix_template_variables table
    op.drop_constraint('fk_matrix_template_variables_company', 'matrix_template_variables', type_='foreignkey')
    op.drop_column('matrix_template_variables', 'company_id')
    #
    ## Remove company_id from matrix_cells table
    op.drop_constraint('fk_matrix_cells_company', 'matrix_cells', type_='foreignkey')
    op.drop_column('matrix_cells', 'company_id')

    ## Remove company_id from matrices table
    op.drop_constraint('fk_matrices_company', 'matrices', type_='foreignkey')
    op.drop_column('matrices', 'company_id')
    #
    ## Remove company_id from documents table
    #op.drop_constraint(None, 'documents', type_='foreignkey')
    #op.drop_column('documents', 'company_id')
