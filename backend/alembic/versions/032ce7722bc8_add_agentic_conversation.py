"""add_agentic_conversation

Revision ID: 032ce7722bc8
Revises: dd1e3b16f73b
Create Date: 2025-09-04 18:41:23.868812

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '032ce7722bc8'
down_revision: Union[str, Sequence[str], None] = 'dd1e3b16f73b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('ai_model_id', sa.BigInteger(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['ai_model_id'], ['ai_models.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_id'), 'conversations', ['id'], unique=False)
    op.create_index(op.f('ix_conversations_ai_model_id'), 'conversations', ['ai_model_id'], unique=False)
    op.create_index(op.f('ix_conversations_is_active'), 'conversations', ['is_active'], unique=False)
    op.create_index(op.f('ix_conversations_deleted'), 'conversations', ['deleted'], unique=False)

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('conversation_id', sa.BigInteger(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('tool_calls', sa.JSON(), nullable=True),
        sa.Column('tool_call_id', sa.String(length=255), nullable=True),
        sa.Column('sequence_number', sa.Integer(), nullable=False),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_id'), 'messages', ['id'], unique=False)
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_messages_role'), 'messages', ['role'], unique=False)
    op.create_index(op.f('ix_messages_tool_call_id'), 'messages', ['tool_call_id'], unique=False)
    op.create_index(op.f('ix_messages_sequence_number'), 'messages', ['sequence_number'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop messages table
    op.drop_index(op.f('ix_messages_sequence_number'), table_name='messages')
    op.drop_index(op.f('ix_messages_tool_call_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_role'), table_name='messages')
    op.drop_index(op.f('ix_messages_conversation_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_id'), table_name='messages')
    op.drop_table('messages')
    
    # Drop conversations table
    op.drop_index(op.f('ix_conversations_deleted'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_is_active'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_ai_model_id'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_id'), table_name='conversations')
    op.drop_table('conversations')
