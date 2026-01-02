"""separate_document_entity

Revision ID: a06adee7f5fe
Revises: 085b19cca784
Create Date: 2025-08-01 14:16:29.735139

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a06adee7f5fe'
down_revision: Union[str, Sequence[str], None] = '085b19cca784'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the new matrix_documents junction table
    op.create_table(
        'matrix_documents',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('matrix_id', sa.BigInteger(), nullable=False),
        sa.Column('document_id', sa.BigInteger(), nullable=False),
        sa.Column('label', sa.String(), nullable=True),
        sa.Column('deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['matrix_id'], ['matrices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_matrix_documents_deleted'), 'matrix_documents', ['deleted'], unique=False)
    op.create_index(op.f('ix_matrix_documents_document_id'), 'matrix_documents', ['document_id'], unique=False)
    op.create_index(op.f('ix_matrix_documents_id'), 'matrix_documents', ['id'], unique=False)
    op.create_index(op.f('ix_matrix_documents_matrix_id'), 'matrix_documents', ['matrix_id'], unique=False)

    # Migrate existing data from documents to matrix_documents
    connection = op.get_bind()
    connection.execute(sa.text("""
        INSERT INTO matrix_documents (matrix_id, document_id, label, deleted, created_at, updated_at)
        SELECT matrix_id, id, label, deleted, created_at, updated_at
        FROM documents
        WHERE deleted = false
    """))

    # Drop the foreign key constraint and columns from documents table
    op.drop_constraint('documents_matrix_id_fkey', 'documents', type_='foreignkey')
    op.drop_index('ix_documents_matrix_id', table_name='documents')
    op.drop_column('documents', 'matrix_id')
    op.drop_column('documents', 'label')

def downgrade() -> None:
    # Add back the matrix_id and label columns to documents table
    op.add_column('documents', sa.Column('matrix_id', sa.BigInteger(), nullable=True))
    op.add_column('documents', sa.Column('label', sa.String(), nullable=True))
    
    # Restore data from matrix_documents back to documents
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE documents 
        SET matrix_id = md.matrix_id, label = md.label
        FROM matrix_documents md
        WHERE documents.id = md.document_id
    """))
    
    # Make matrix_id non-nullable and add constraints
    op.alter_column('documents', 'matrix_id', nullable=False)
    op.create_index('ix_documents_matrix_id', 'documents', ['matrix_id'], unique=False)
    op.create_foreign_key('documents_matrix_id_fkey', 'documents', 'matrices', ['matrix_id'], ['id'])
    
    # Drop the matrix_documents table
    op.drop_index(op.f('ix_matrix_documents_matrix_id'), table_name='matrix_documents')
    op.drop_index(op.f('ix_matrix_documents_id'), table_name='matrix_documents')
    op.drop_index(op.f('ix_matrix_documents_document_id'), table_name='matrix_documents')
    op.drop_index(op.f('ix_matrix_documents_deleted'), table_name='matrix_documents')
    op.drop_table('matrix_documents')