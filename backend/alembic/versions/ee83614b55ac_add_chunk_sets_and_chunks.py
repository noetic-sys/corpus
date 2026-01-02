"""add_chunk_sets_and_chunks

Revision ID: ee83614b55ac
Revises: 2fd5369a5190
Create Date: 2025-11-05 22:23:18.764992

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ee83614b55ac'
down_revision: Union[str, Sequence[str], None] = '2fd5369a5190'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create chunk_sets table
    op.create_table(
        'chunk_sets',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('document_id', sa.BigInteger(), nullable=False),
        sa.Column('company_id', sa.BigInteger(), nullable=False),
        sa.Column('chunking_strategy', sa.String(), nullable=False),
        sa.Column('total_chunks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('s3_prefix', sa.String(), nullable=False),
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chunk_sets_id'), 'chunk_sets', ['id'], unique=False)
    op.create_index(op.f('ix_chunk_sets_document_id'), 'chunk_sets', ['document_id'], unique=False)
    op.create_index(op.f('ix_chunk_sets_company_id'), 'chunk_sets', ['company_id'], unique=False)
    op.create_index(op.f('ix_chunk_sets_deleted'), 'chunk_sets', ['deleted'], unique=False)

    # Create chunks table
    op.create_table(
        'chunks',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('chunk_set_id', sa.BigInteger(), nullable=False),
        sa.Column('chunk_id', sa.String(), nullable=False),
        sa.Column('document_id', sa.BigInteger(), nullable=False),
        sa.Column('company_id', sa.BigInteger(), nullable=False),
        sa.Column('s3_key', sa.String(), nullable=False),
        sa.Column('chunk_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('chunk_order', sa.Integer(), nullable=False),
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['chunk_set_id'], ['chunk_sets.id'], ),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chunks_id'), 'chunks', ['id'], unique=False)
    op.create_index(op.f('ix_chunks_chunk_set_id'), 'chunks', ['chunk_set_id'], unique=False)
    op.create_index(op.f('ix_chunks_chunk_id'), 'chunks', ['chunk_id'], unique=False)
    op.create_index(op.f('ix_chunks_document_id'), 'chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_chunks_company_id'), 'chunks', ['company_id'], unique=False)
    op.create_index(op.f('ix_chunks_deleted'), 'chunks', ['deleted'], unique=False)

    # Add current_chunk_set_id to documents table
    op.add_column(
        'documents',
        sa.Column('current_chunk_set_id', sa.BigInteger(), nullable=True)
    )
    op.create_foreign_key(
        'fk_documents_current_chunk_set_id',
        'documents', 'chunk_sets',
        ['current_chunk_set_id'], ['id']
    )
    op.create_index(op.f('ix_documents_current_chunk_set_id'), 'documents', ['current_chunk_set_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove current_chunk_set_id from documents table
    op.drop_index(op.f('ix_documents_current_chunk_set_id'), table_name='documents')
    op.drop_constraint('fk_documents_current_chunk_set_id', 'documents', type_='foreignkey')
    op.drop_column('documents', 'current_chunk_set_id')

    # Drop chunks table
    op.drop_index(op.f('ix_chunks_deleted'), table_name='chunks')
    op.drop_index(op.f('ix_chunks_company_id'), table_name='chunks')
    op.drop_index(op.f('ix_chunks_document_id'), table_name='chunks')
    op.drop_index(op.f('ix_chunks_chunk_id'), table_name='chunks')
    op.drop_index(op.f('ix_chunks_chunk_set_id'), table_name='chunks')
    op.drop_index(op.f('ix_chunks_id'), table_name='chunks')
    op.drop_table('chunks')

    # Drop chunk_sets table
    op.drop_index(op.f('ix_chunk_sets_deleted'), table_name='chunk_sets')
    op.drop_index(op.f('ix_chunk_sets_company_id'), table_name='chunk_sets')
    op.drop_index(op.f('ix_chunk_sets_document_id'), table_name='chunk_sets')
    op.drop_index(op.f('ix_chunk_sets_id'), table_name='chunk_sets')
    op.drop_table('chunk_sets')
