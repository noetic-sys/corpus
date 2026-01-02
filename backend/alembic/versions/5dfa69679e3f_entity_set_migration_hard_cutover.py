"""entity_set_migration_hard_cutover

Revision ID: 5dfa69679e3f
Revises: 814b0770e36e
Create Date: 2025-10-13 20:33:27.514206

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5dfa69679e3f'
down_revision: Union[str, Sequence[str], None] = '814b0770e36e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Entity Set Migration (HARD CUTOVER).

    This is a hard migration with no backwards compatibility.
    Migrates from rigid document×question matrix model to flexible entity set model.

    Changes:
    - Add matrix_type and cell_type columns
    - Create 3 new entity set tables
    - DROP document_id and question_id from matrix_cells (HARD MIGRATION!)
    - DROP matrix_documents table (no longer needed)
    """

    # Step 1: Add matrix_type column to matrices table
    op.add_column('matrices',
        sa.Column('matrix_type', sa.String(), nullable=False,
                  server_default='standard')
    )
    op.create_index(op.f('ix_matrices_matrix_type'), 'matrices', ['matrix_type'], unique=False)

    # Step 2: Add cell_type column to matrix_cells table
    # NOT NULL because QA worker needs it to determine processing strategy
    op.add_column('matrix_cells',
        sa.Column('cell_type', sa.String(), nullable=False, server_default='standard')
    )

    # Step 3: Create matrix_entity_sets table
    op.create_table(
        'matrix_entity_sets',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('matrix_id', sa.BigInteger(), nullable=False),
        sa.Column('company_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['matrix_id'], ['matrices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_matrix_entity_sets_id'), 'matrix_entity_sets', ['id'], unique=False)
    op.create_index(op.f('ix_matrix_entity_sets_company_id'), 'matrix_entity_sets', ['company_id'], unique=False)
    op.create_index('idx_entity_set_matrix', 'matrix_entity_sets', ['matrix_id'], unique=False)

    # Step 4: Create matrix_entity_set_members table
    op.create_table(
        'matrix_entity_set_members',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('entity_set_id', sa.BigInteger(), nullable=False),
        sa.Column('company_id', sa.BigInteger(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.BigInteger(), nullable=False),
        sa.Column('member_order', sa.Integer(), nullable=False, default=0, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['entity_set_id'], ['matrix_entity_sets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_matrix_entity_set_members_id'), 'matrix_entity_set_members', ['id'], unique=False)
    op.create_index(op.f('ix_matrix_entity_set_members_company_id'), 'matrix_entity_set_members', ['company_id'], unique=False)
    op.create_index('idx_member_entity_set', 'matrix_entity_set_members', ['entity_set_id'], unique=False)
    op.create_index('idx_member_lookup', 'matrix_entity_set_members', ['entity_set_id', 'entity_type', 'entity_id'], unique=False)

    # Step 5: Create matrix_cell_entity_refs table (N-dimensional coordinate system)
    op.create_table(
        'matrix_cell_entity_refs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('matrix_id', sa.BigInteger(), nullable=False),
        sa.Column('matrix_cell_id', sa.BigInteger(), nullable=False),
        sa.Column('entity_set_id', sa.BigInteger(), nullable=False),
        sa.Column('entity_set_member_id', sa.BigInteger(), nullable=False),
        sa.Column('company_id', sa.BigInteger(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),  # REQUIRED: axis identifier
        sa.Column('entity_order', sa.Integer(), nullable=False, default=0, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['matrix_id'], ['matrices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['matrix_cell_id'], ['matrix_cells.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_set_id'], ['matrix_entity_sets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_set_member_id'], ['matrix_entity_set_members.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_matrix_cell_entity_refs_id'), 'matrix_cell_entity_refs', ['id'], unique=False)
    op.create_index(op.f('ix_matrix_cell_entity_refs_company_id'), 'matrix_cell_entity_refs', ['company_id'], unique=False)
    op.create_index('idx_cell_entity_lookup', 'matrix_cell_entity_refs', ['matrix_cell_id', 'role'], unique=False)
    op.create_index('idx_entity_set_filter', 'matrix_cell_entity_refs', ['matrix_id', 'entity_set_id', 'entity_set_member_id', 'role'], unique=False)

    # Step 6: DROP old columns from matrix_cells (HARD MIGRATION!)
    # WARNING: This will lose all existing cell data!
    op.drop_index('ix_matrix_cells_document_id', table_name='matrix_cells')
    op.drop_index('ix_matrix_cells_question_id', table_name='matrix_cells')
    op.drop_constraint('matrix_cells_document_id_fkey', 'matrix_cells', type_='foreignkey')
    op.drop_constraint('matrix_cells_question_id_fkey', 'matrix_cells', type_='foreignkey')
    op.drop_column('matrix_cells', 'document_id')
    op.drop_column('matrix_cells', 'question_id')

    # Step 7: DROP matrix_documents table (no longer needed)
    # WARNING: This will lose all existing matrix-document associations!
    op.drop_index('ix_matrix_documents_matrix_id', table_name='matrix_documents')
    op.drop_index('ix_matrix_documents_document_id', table_name='matrix_documents')
    op.drop_index('ix_matrix_documents_deleted', table_name='matrix_documents')
    op.drop_index('ix_matrix_documents_id', table_name='matrix_documents')
    op.drop_table('matrix_documents')


def downgrade() -> None:
    """Downgrade schema - Restore old rigid matrix model.

    WARNING: This is a lossy downgrade!
    Entity set data will be lost and cannot be converted back to the old model.
    Only use this for development rollback.
    """

    # Step 1: Recreate matrix_documents table
    # Must match the state after a40cb53a0189 (add_company_id) was applied
    op.create_table(
        'matrix_documents',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('matrix_id', sa.BigInteger(), nullable=False),
        sa.Column('document_id', sa.BigInteger(), nullable=False),
        sa.Column('label', sa.String(), nullable=True),
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('company_id', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['matrix_id'], ['matrices.id'], ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name='fk_matrix_documents_company'),
        sa.PrimaryKeyConstraint('id')
    )
    # Recreate indexes using op.f() for consistency with a06adee7f5fe
    op.create_index(op.f('ix_matrix_documents_deleted'), 'matrix_documents', ['deleted'], unique=False)
    op.create_index(op.f('ix_matrix_documents_document_id'), 'matrix_documents', ['document_id'], unique=False)
    op.create_index(op.f('ix_matrix_documents_id'), 'matrix_documents', ['id'], unique=False)
    op.create_index(op.f('ix_matrix_documents_matrix_id'), 'matrix_documents', ['matrix_id'], unique=False)
    # company_id index was added by a40cb53a0189
    op.create_index('ix_matrix_documents_company_id', 'matrix_documents', ['company_id'], unique=False)
    # Composite indexes were added by dd1e3b16f73b
    op.create_index('ix_matrix_documents_id_deleted', 'matrix_documents', ['id', 'deleted'], unique=False)
    op.create_index('ix_matrix_docs_matrix_del', 'matrix_documents', ['matrix_id', 'deleted'], unique=False)
    op.create_index('ix_matrix_docs_doc_del', 'matrix_documents', ['document_id', 'deleted'], unique=False)
    op.create_index('ix_matrix_docs_matrix_doc_del', 'matrix_documents', ['matrix_id', 'document_id', 'deleted'], unique=False)

    # Step 2: Add back document_id and question_id columns to matrix_cells
    op.add_column('matrix_cells',
        sa.Column('document_id', sa.BigInteger(), nullable=True)  # Nullable since we have no data
    )
    op.add_column('matrix_cells',
        sa.Column('question_id', sa.BigInteger(), nullable=True)  # Nullable since we have no data
    )
    op.create_foreign_key('matrix_cells_document_id_fkey', 'matrix_cells', 'documents', ['document_id'], ['id'])
    op.create_foreign_key('matrix_cells_question_id_fkey', 'matrix_cells', 'questions', ['question_id'], ['id'])
    op.create_index('ix_matrix_cells_document_id', 'matrix_cells', ['document_id'], unique=False)
    op.create_index('ix_matrix_cells_question_id', 'matrix_cells', ['question_id'], unique=False)
    # Composite indexes from dd1e3b16f73b that were auto-dropped when document_id/question_id were dropped
    # NOTE: ix_matrix_cells_id_deleted and ix_matrix_cells_matrix_del still exist (they don't use document_id/question_id)
    op.create_index('ix_matrix_cells_doc_q_del', 'matrix_cells', ['document_id', 'question_id', 'deleted'], unique=False)
    op.create_index('ix_matrix_cells_matrix_doc_del', 'matrix_cells', ['matrix_id', 'document_id', 'deleted'], unique=False)
    op.create_index('ix_matrix_cells_matrix_q_del', 'matrix_cells', ['matrix_id', 'question_id', 'deleted'], unique=False)
    op.create_index('ix_matrix_cells_matrix_doc_q_del', 'matrix_cells', ['matrix_id', 'document_id', 'question_id', 'deleted'], unique=False)

    # Step 3: Drop entity set tables (in reverse order due to foreign keys)
    op.drop_index('idx_entity_set_filter', table_name='matrix_cell_entity_refs')
    op.drop_index('idx_cell_entity_lookup', table_name='matrix_cell_entity_refs')
    op.drop_index(op.f('ix_matrix_cell_entity_refs_id'), table_name='matrix_cell_entity_refs')
    op.drop_table('matrix_cell_entity_refs')

    op.drop_index('idx_member_lookup', table_name='matrix_entity_set_members')
    op.drop_index('idx_member_entity_set', table_name='matrix_entity_set_members')
    op.drop_index(op.f('ix_matrix_entity_set_members_id'), table_name='matrix_entity_set_members')
    op.drop_table('matrix_entity_set_members')

    op.drop_index('idx_entity_set_matrix', table_name='matrix_entity_sets')
    op.drop_index(op.f('ix_matrix_entity_sets_id'), table_name='matrix_entity_sets')
    op.drop_table('matrix_entity_sets')

    # Step 4: Remove new columns
    op.drop_column('matrix_cells', 'cell_type')

    op.drop_index(op.f('ix_matrices_matrix_type'), table_name='matrices')
    op.drop_column('matrices', 'matrix_type')
