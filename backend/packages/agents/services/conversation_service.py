from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from packages.agents.repositories.conversation_repository import ConversationRepository
from packages.agents.repositories.message_repository import MessageRepository
from packages.agents.models.domain.conversation import (
    ConversationModel,
    ConversationCreateModel,
    ConversationUpdateModel,
)
from packages.agents.models.domain.message import MessageModel, MessageCreateModel
from packages.agents.models.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
)
from packages.agents.models.schemas.message import MessageCreate
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class ConversationService:
    """Service for handling conversation operations."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.conversation_repo = ConversationRepository(db_session)
        self.message_repo = MessageRepository(db_session)

    @trace_span
    async def create_conversation(
        self, conversation_data: ConversationCreate, company_id: int
    ) -> ConversationModel:
        """Create a new conversation."""
        logger.info(f"Creating conversation: {conversation_data.title}")

        create_model = ConversationCreateModel(
            company_id=company_id, **conversation_data.model_dump()
        )
        conversation = await self.conversation_repo.create(create_model)

        logger.info(f"Created conversation with ID: {conversation.id}")
        return conversation

    @trace_span
    async def get_conversation(
        self, conversation_id: int, company_id: Optional[int] = None
    ) -> Optional[ConversationModel]:
        """Get a conversation by ID."""
        return await self.conversation_repo.get(conversation_id, company_id)

    @trace_span
    async def update_conversation(
        self,
        conversation_id: int,
        conversation_update: ConversationUpdate,
        company_id: Optional[int] = None,
    ) -> Optional[ConversationModel]:
        """Update a conversation."""
        existing_conversation = await self.conversation_repo.get(
            conversation_id, company_id
        )
        if not existing_conversation:
            return None

        update_data = conversation_update.model_dump(exclude_unset=True)
        conversation = await self.conversation_repo.update(conversation_id, update_data)
        if conversation:
            logger.info(f"Updated conversation {conversation_id}")
        return conversation

    @trace_span
    async def delete_conversation(
        self, conversation_id: int, company_id: Optional[int] = None
    ) -> bool:
        """Delete a conversation (soft delete by deactivating)."""
        conversation = await self.conversation_repo.deactivate_conversation(
            conversation_id, company_id
        )
        success = conversation is not None
        if success:
            logger.info(f"Deactivated conversation {conversation_id}")
        return success

    @trace_span
    async def get_active_conversations(
        self, company_id: Optional[int] = None
    ) -> List[ConversationModel]:
        """Get all active conversations."""
        return await self.conversation_repo.get_active_conversations(company_id)

    @trace_span
    async def add_message(
        self, message_data: MessageCreate, conversation_id: int, company_id: int
    ) -> MessageModel:
        """Add a message to a conversation."""
        # Verify conversation exists
        conversation = await self.conversation_repo.get(conversation_id, company_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Get next sequence number
        sequence_number = await self.message_repo.get_next_sequence_number(
            conversation_id, company_id
        )

        # Create message
        create_model = MessageCreateModel(
            conversation_id=conversation_id,
            company_id=company_id,
            sequence_number=sequence_number,
            **message_data.model_dump(),
        )
        message = await self.message_repo.create(create_model)

        # Update conversation's updated_at timestamp
        update_model = ConversationUpdateModel(updated_at=message.created_at)
        await self.conversation_repo.update(conversation_id, update_model)

        logger.info(f"Added message to conversation {conversation_id}")
        return message

    @trace_span
    async def get_conversation_messages(
        self,
        conversation_id: int,
        limit: Optional[int] = None,
        company_id: Optional[int] = None,
    ) -> List[MessageModel]:
        """Get all messages for a conversation."""
        # Verify conversation exists
        conversation = await self.conversation_repo.get(conversation_id, company_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return await self.message_repo.get_by_conversation_id(
            conversation_id, limit, company_id
        )

    @trace_span
    async def get_latest_messages(
        self, conversation_id: int, count: int = 10, company_id: Optional[int] = None
    ) -> List[MessageModel]:
        """Get the latest N messages from a conversation."""
        # Verify conversation exists
        conversation = await self.conversation_repo.get(conversation_id, company_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return await self.message_repo.get_latest_by_conversation_id(
            conversation_id, count, company_id
        )

    @trace_span
    async def get_message_count(
        self, conversation_id: int, company_id: Optional[int] = None
    ) -> int:
        """Get the total number of messages in a conversation."""
        return await self.message_repo.count_by_conversation_id(
            conversation_id, company_id
        )


def get_conversation_service(db_session: AsyncSession) -> ConversationService:
    """Get conversation service instance."""
    return ConversationService(db_session)
