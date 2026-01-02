from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.session import get_db, get_db_readonly
from common.db.transaction_utils import transaction
from packages.auth.dependencies import get_current_active_user
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.agents.models.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
)
from packages.agents.models.schemas.message import (
    MessageCreate,
    MessageResponse,
)
from packages.agents.services.conversation_service import get_conversation_service
from packages.agents.services.agent_service import get_agent_service
from common.core.otel_axiom_exporter import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/conversations/", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation."""
    async with transaction(db):
        conversation_service = get_conversation_service(db)
        return await conversation_service.create_conversation(
            conversation, current_user.company_id
        )


@router.get("/conversations/{conversationId}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: Annotated[int, Path(alias="conversationId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_readonly),
):
    """Get a conversation by ID."""
    conversation_service = get_conversation_service(db)
    conversation = await conversation_service.get_conversation(
        conversation_id, current_user.company_id
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/conversations/", response_model=List[ConversationResponse])
async def get_active_conversations(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_readonly),
):
    """Get all active conversations."""
    conversation_service = get_conversation_service(db)
    return await conversation_service.get_active_conversations(current_user.company_id)


@router.patch("/conversations/{conversationId}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: Annotated[int, Path(alias="conversationId")],
    conversation_update: ConversationUpdate,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a conversation."""
    async with transaction(db):
        conversation_service = get_conversation_service(db)
        conversation = await conversation_service.update_conversation(
            conversation_id, conversation_update, current_user.company_id
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation


@router.delete("/conversations/{conversationId}")
async def delete_conversation(
    conversation_id: Annotated[int, Path(alias="conversationId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete (deactivate) a conversation."""
    async with transaction(db):
        conversation_service = get_conversation_service(db)
        success = await conversation_service.delete_conversation(
            conversation_id, current_user.company_id
        )
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"message": "Conversation deleted successfully"}


@router.get(
    "/conversations/{conversationId}/messages/", response_model=List[MessageResponse]
)
async def get_conversation_messages(
    conversation_id: Annotated[int, Path(alias="conversationId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_readonly),
):
    """Get all messages for a conversation."""
    conversation_service = get_conversation_service(db)
    return await conversation_service.get_conversation_messages(
        conversation_id, None, current_user.company_id
    )


@router.post(
    "/conversations/{conversationId}/messages/", response_model=List[MessageResponse]
)
async def send_message_to_agent(
    conversation_id: Annotated[int, Path(alias="conversationId")],
    message: MessageCreate,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the agent and get the response(s)."""
    async with transaction(db):
        agent_service = get_agent_service(db)

        if message.role != "user":
            raise HTTPException(
                status_code=400, detail="Only user messages can be sent to the agent"
            )

        if not message.content:
            raise HTTPException(status_code=400, detail="Message content is required")

        logger.info(f"Processing user message in conversation {conversation_id}")

        # Process the message with the agent (this includes adding the user message)
        generated_messages = await agent_service.process_user_message(
            conversation_id,
            message.content,
            current_user,
            permission_mode=message.permission_mode,
            extra_data=message.extra_data,
        )

        logger.info(f"Agent generated {len(generated_messages)} messages")
        return generated_messages


@router.post(
    "/conversations/{conversationId}/messages/manual/", response_model=MessageResponse
)
async def add_manual_message(
    conversation_id: Annotated[int, Path(alias="conversationId")],
    message: MessageCreate,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually add a message to a conversation (for testing/debugging)."""
    async with transaction(db):
        conversation_service = get_conversation_service(db)
        return await conversation_service.add_message(
            message, conversation_id, current_user.company_id
        )
