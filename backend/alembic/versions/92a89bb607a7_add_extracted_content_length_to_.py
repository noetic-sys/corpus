"""add_extracted_content_length_to_documents

Revision ID: 92a89bb607a7
Revises: 5bd5e08b35df
Create Date: 2026-01-02 21:27:19.607895

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92a89bb607a7'
down_revision: Union[str, Sequence[str], None] = '5bd5e08b35df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add extracted_text_char_count column to documents table.

    Stores the character count of extracted text content, enabling
    size-based routing to agentic QA without fetching content from S3.
    Used to determine if document is too large for regular QA context window.
    Nullable to support existing documents (lazy backfill on first QA access).
    """
    op.add_column(
        'documents',
        sa.Column('extracted_text_char_count', sa.BigInteger(), nullable=True)
    )


def downgrade() -> None:
    """Remove extracted_text_char_count column from documents table."""
    op.drop_column('documents', 'extracted_text_char_count')
