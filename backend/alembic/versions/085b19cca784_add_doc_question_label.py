"""add_doc_question_label

Revision ID: 085b19cca784
Revises: 5ce249d08456
Create Date: 2025-08-01 13:15:02.262290

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '085b19cca784'
down_revision: Union[str, Sequence[str], None] = '5ce249d08456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add label column to documents table
    op.add_column('documents', sa.Column('label', sa.String(), nullable=True))
    
    # Add label column to questions table
    op.add_column('questions', sa.Column('label', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove label column from questions table
    op.drop_column('questions', 'label')
    
    # Remove label column from documents table
    op.drop_column('documents', 'label')