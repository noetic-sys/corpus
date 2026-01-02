"""document_checksum

Revision ID: 32bd92b38258
Revises: 38c7f6b94a1f
Create Date: 2025-08-02 21:34:13.581219

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '32bd92b38258'
down_revision: Union[str, Sequence[str], None] = '38c7f6b94a1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add checksum column to documents table
    op.add_column('documents', sa.Column('checksum', sa.String(), nullable=False))
    
    # Create index on checksum column
    op.create_index('ix_documents_checksum', 'documents', ['checksum'])
    
    # Create unique constraint on checksum
    op.create_unique_constraint('uq_documents_checksum', 'documents', ['checksum'])

def downgrade() -> None:
    """Downgrade schema."""
    # Drop unique constraint
    op.drop_constraint('uq_documents_checksum', 'documents', type_='unique')
    
    # Drop index
    op.drop_index('ix_documents_checksum', 'documents')
    
    # Drop checksum column
    op.drop_column('documents', 'checksum')
