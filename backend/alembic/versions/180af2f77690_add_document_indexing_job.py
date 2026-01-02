"""add_document_indexing_job

Revision ID: 180af2f77690
Revises: a140c72a9ef5
Create Date: 2025-08-28 15:30:16.797809

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '180af2f77690'
down_revision: Union[str, Sequence[str], None] = 'a140c72a9ef5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'document_indexing_jobs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('worker_message_id', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_indexing_jobs_id'), 'document_indexing_jobs', ['id'], unique=False)
    op.create_index('ix_document_indexing_jobs_document_id', 'document_indexing_jobs', ['document_id'], unique=False)
    op.create_index('ix_document_indexing_jobs_status', 'document_indexing_jobs', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_document_indexing_jobs_status', table_name='document_indexing_jobs')
    op.drop_index('ix_document_indexing_jobs_document_id', table_name='document_indexing_jobs')
    op.drop_index(op.f('ix_document_indexing_jobs_id'), table_name='document_indexing_jobs')
    op.drop_table('document_indexing_jobs')
