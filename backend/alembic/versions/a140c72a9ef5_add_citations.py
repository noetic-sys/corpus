"""add_citations

Revision ID: a140c72a9ef5
Revises: 2eee1325ba41
Create Date: 2025-08-27 16:36:33.226534

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a140c72a9ef5'
down_revision: Union[str, Sequence[str], None] = '2eee1325ba41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create citation_sets table
    op.create_table(
        'citation_sets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('answer_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['answer_id'], ['answers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_citation_sets_id'), 'citation_sets', ['id'])
    op.create_index(op.f('ix_citation_sets_answer_id'), 'citation_sets', ['answer_id'])

    # Create citations table
    op.create_table(
        'citations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('citation_set_id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('quote_text', sa.Text(), nullable=False),
        sa.Column('citation_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['citation_set_id'], ['citation_sets.id']),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_citations_id'), 'citations', ['id'])
    op.create_index(op.f('ix_citations_citation_set_id'), 'citations', ['citation_set_id'])
    op.create_index(op.f('ix_citations_document_id'), 'citations', ['document_id'])

    # Add current_citation_set_id to answers table
    op.add_column('answers', sa.Column('current_citation_set_id', sa.BigInteger(), nullable=True))
    op.create_index(op.f('ix_answers_current_citation_set_id'), 'answers', ['current_citation_set_id'])
    op.create_foreign_key('fk_answers_current_citation_set_id', 'answers', 'citation_sets', ['current_citation_set_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop current_citation_set_id and its constraints from answers
    op.drop_constraint('fk_answers_current_citation_set_id', 'answers', type_='foreignkey')
    op.drop_index(op.f('ix_answers_current_citation_set_id'), table_name='answers')
    op.drop_column('answers', 'current_citation_set_id')

    # Drop citations table
    op.drop_index(op.f('ix_citations_document_id'), table_name='citations')
    op.drop_index(op.f('ix_citations_citation_set_id'), table_name='citations')
    op.drop_index(op.f('ix_citations_id'), table_name='citations')
    op.drop_table('citations')

    # Drop citation_sets table
    op.drop_index(op.f('ix_citation_sets_answer_id'), table_name='citation_sets')
    op.drop_index(op.f('ix_citation_sets_id'), table_name='citation_sets')
    op.drop_table('citation_sets')
