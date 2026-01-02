"""add_question_types_table_and_question_type_id

Revision ID: c30a4e87d243
Revises: 4e3f7c3be89a
Create Date: 2025-07-27 14:40:41.618849

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c30a4e87d243'
down_revision: Union[str, Sequence[str], None] = '4e3f7c3be89a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create question_types table
    op.create_table('question_types',
        sa.Column('id', sa.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('name', sa.VARCHAR(), nullable=False),
        sa.Column('description', sa.TEXT(), nullable=True),
        sa.Column('validation_schema', sa.JSON(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('question_types_pkey'))
    )
    op.create_index(op.f('ix_question_types_id'), 'question_types', ['id'], unique=False)
    op.create_index(op.f('ix_question_types_name'), 'question_types', ['name'], unique=True)
    
    # Insert default question types
    question_types_table = sa.table('question_types',
        sa.column('id', sa.BIGINT()),
        sa.column('name', sa.VARCHAR()),
        sa.column('description', sa.TEXT()),
        sa.column('validation_schema', sa.JSON())
    )
    
    op.bulk_insert(question_types_table, [
        {'id': 1, 'name': 'SHORT_ANSWER', 'description': 'Brief text responses (≤200 characters)', 'validation_schema': {'max_length': 200}},
        {'id': 2, 'name': 'LONG_ANSWER', 'description': 'Extended text responses (>200 characters)', 'validation_schema': {'min_length': 1}},
        {'id': 3, 'name': 'DATE', 'description': 'Date values with format validation', 'validation_schema': {'format': 'date', 'output_format': 'ISO'}},
        {'id': 4, 'name': 'CURRENCY', 'description': 'Monetary amounts with currency detection', 'validation_schema': {'format': 'currency', 'detect_currency': True}},
        {'id': 5, 'name': 'SINGLE_SELECT', 'description': 'Choose one option from predefined values', 'validation_schema': {'type': 'enum', 'options': []}},
    ])
    
    # Add question_type_id column to questions table
    op.add_column('questions', sa.Column('question_type_id', sa.BIGINT(), nullable=False, server_default='1'))
    op.add_column('questions', sa.Column('validation_config', sa.JSON(), nullable=True))
    
    # Create foreign key constraint with CASCADE DELETE
    op.create_foreign_key(op.f('questions_question_type_id_fkey'), 'questions', 'question_types', ['question_type_id'], ['id'], ondelete='CASCADE')
    op.create_index(op.f('ix_questions_question_type_id'), 'questions', ['question_type_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign key constraint and index
    op.drop_index(op.f('ix_questions_question_type_id'), table_name='questions')
    op.drop_constraint(op.f('questions_question_type_id_fkey'), 'questions', type_='foreignkey')
    
    # Remove columns from questions table
    op.drop_column('questions', 'validation_config')
    op.drop_column('questions', 'question_type_id')
    
    # Drop question_types table
    op.drop_index(op.f('ix_question_types_name'), table_name='question_types')
    op.drop_index(op.f('ix_question_types_id'), table_name='question_types')
    op.drop_table('question_types')
