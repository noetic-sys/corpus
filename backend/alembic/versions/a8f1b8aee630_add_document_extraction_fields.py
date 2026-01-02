"""add_document_extraction_fields

Revision ID: a8f1b8aee630
Revises: 222a16db167a
Create Date: 2025-07-29 16:23:32.362412

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a8f1b8aee630'
down_revision: Union[str, Sequence[str], None] = '222a16db167a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # Add extraction fields to documents table
    op.add_column('documents', sa.Column('extracted_content_path', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('extraction_status', sa.String(), nullable=False, server_default='pending'))
    op.add_column('documents', sa.Column('extraction_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('documents', sa.Column('extraction_completed_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add indices for performance
    op.create_index(op.f('ix_documents_extracted_content_path'), 'documents', ['extracted_content_path'], unique=False)
    op.create_index(op.f('ix_documents_extraction_status'), 'documents', ['extraction_status'], unique=False)
    
    # Create document_extraction_jobs table
    op.create_table('document_extraction_jobs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('worker_message_id', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('extracted_content_path', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_extraction_jobs_id'), 'document_extraction_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_document_extraction_jobs_document_id'), 'document_extraction_jobs', ['document_id'], unique=False)
    op.create_index(op.f('ix_document_extraction_jobs_status'), 'document_extraction_jobs', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop document_extraction_jobs table indices
    op.drop_index(op.f('ix_document_extraction_jobs_status'), table_name='document_extraction_jobs')
    op.drop_index(op.f('ix_document_extraction_jobs_document_id'), table_name='document_extraction_jobs')
    op.drop_index(op.f('ix_document_extraction_jobs_id'), table_name='document_extraction_jobs')
    
    # Drop document_extraction_jobs table
    op.drop_table('document_extraction_jobs')
    
    # Remove indices from documents table
    op.drop_index(op.f('ix_documents_extraction_status'), table_name='documents')
    op.drop_index(op.f('ix_documents_extracted_content_path'), table_name='documents')
    
    # Remove columns from documents table
    op.drop_column('documents', 'extraction_completed_at')
    op.drop_column('documents', 'extraction_started_at')
    op.drop_column('documents', 'extraction_status')
    op.drop_column('documents', 'extracted_content_path')