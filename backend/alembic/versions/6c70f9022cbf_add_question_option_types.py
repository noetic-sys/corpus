"""add_question_option_types

Revision ID: 6c70f9022cbf
Revises: c30a4e87d243
Create Date: 2025-07-27 17:54:07.748902

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6c70f9022cbf'
down_revision: Union[str, Sequence[str], None] = 'c30a4e87d243'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create question_option_sets table
    op.create_table('question_option_sets',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('question_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_question_option_sets_id'), 'question_option_sets', ['id'], unique=False)
    op.create_index(op.f('ix_question_option_sets_question_id'), 'question_option_sets', ['question_id'], unique=True)
    
    # Create question_options table
    op.create_table('question_options',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('option_set_id', sa.BigInteger(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['option_set_id'], ['question_option_sets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_question_options_id'), 'question_options', ['id'], unique=False)
    op.create_index(op.f('ix_question_options_option_set_id'), 'question_options', ['option_set_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop question option tables
    op.drop_index(op.f('ix_question_options_option_set_id'), table_name='question_options')
    op.drop_index(op.f('ix_question_options_id'), table_name='question_options')
    op.drop_table('question_options')
    
    op.drop_index(op.f('ix_question_option_sets_question_id'), table_name='question_option_sets')
    op.drop_index(op.f('ix_question_option_sets_id'), table_name='question_option_sets')
    op.drop_table('question_option_sets')
