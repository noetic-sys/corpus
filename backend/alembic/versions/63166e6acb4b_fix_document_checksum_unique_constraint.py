"""fix_document_checksum_unique_constraint

Revision ID: 63166e6acb4b
Revises: ee83614b55ac
Create Date: 2025-11-09 17:50:34.800009

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63166e6acb4b'
down_revision: Union[str, Sequence[str], None] = 'ee83614b55ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Replace global unique constraint on checksum with a partial unique constraint
    on (company_id, checksum) where deleted = false.

    This allows:
    - Same document (checksum) to exist in different companies
    - Deleted documents don't block re-upload of same file
    """
    # Drop the old global unique constraint
    op.drop_constraint('uq_documents_checksum', 'documents', type_='unique')

    # Create new partial unique constraint (company_id, checksum) where not deleted
    # Note: PostgreSQL partial indexes require raw SQL
    op.create_index(
        'uq_documents_company_checksum_not_deleted',
        'documents',
        ['company_id', 'checksum'],
        unique=True,
        postgresql_where=sa.text('deleted = false')
    )


def downgrade() -> None:
    """Revert to global unique constraint on checksum."""
    # Drop the partial unique constraint
    op.drop_index(
        'uq_documents_company_checksum_not_deleted',
        table_name='documents'
    )

    # Restore old global unique constraint
    # Note: This will fail if there are duplicate checksums across companies
    op.create_unique_constraint('uq_documents_checksum', 'documents', ['checksum'])
