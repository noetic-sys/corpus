import json
from typing import Dict, Union, Optional
from pydantic import ValidationError
from fastapi import WebSocket, WebSocketDisconnect

from common.db.session import get_db
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.auth.dependencies import get_current_active_user_from_token
from packages.agents.services.conversation_service import ConversationService
from packages.agents.services.agent_service import AgentService
from packages.agents.models.schemas.conversation import ConversationCreate
from packages.agents.models.schemas.websocket import (
    ClientMessage,
    ServerMessage,
    UserMessageRequest,
    GetHistoryRequest,
    PingRequest,
    ConnectedResponse,
    MessageReceivedResponse,
    AgentMessageResponse,
    ResponseCompleteResponse,
    ConversationHistoryResponse,
    ErrorResponse,
    PongResponse,
)
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time chat."""

    def __init__(self):
        # conversation_id -> WebSocket
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, conversation_id: int):
        """Accept a WebSocket connection for a conversation."""
        await websocket.accept()
        self.active_connections[conversation_id] = websocket
        logger.info(f"WebSocket connected for conversation {conversation_id}")

    def disconnect(self, conversation_id: int):
        """Remove a WebSocket connection."""
        if conversation_id in self.active_connections:
            del self.active_connections[conversation_id]
            logger.info(f"WebSocket disconnected for conversation {conversation_id}")

    async def send_message(self, conversation_id: int, message: ServerMessage):
        """Send a typed message to a specific conversation's WebSocket."""
        if conversation_id in self.active_connections:
            websocket = self.active_connections[conversation_id]
            # Convert to JSON using pydantic's serialization
            message_json = message.model_dump_json(by_alias=True)
            await websocket.send_text(message_json)

    async def send_error(self, conversation_id: int, error: str, code: str = None):
        """Send an error message to a specific conversation's WebSocket."""
        error_response = ErrorResponse(error=error, code=code)
        await self.send_message(conversation_id, error_response)


# Global WebSocket manager
ws_manager = WebSocketManager()


def parse_client_message(data: str) -> Union[ClientMessage, None]:
    """Parse incoming JSON data into a typed client message."""
    try:
        raw_data = json.loads(data)
        message_type = raw_data.get("type")

        if message_type == "user_message":
            return UserMessageRequest.model_validate(raw_data)
        elif message_type == "get_history":
            return GetHistoryRequest.model_validate(raw_data)
        elif message_type == "ping":
            return PingRequest.model_validate(raw_data)
        else:
            logger.warning(f"Unknown message type: {message_type}")
            return None

    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Error parsing client message: {e}")
        return None


async def websocket_chat_endpoint(
    websocket: WebSocket, conversation_id: int, token: Optional[str] = None
):
    """WebSocket endpoint for real-time chat with agents."""
    await ws_manager.connect(websocket, conversation_id)

    # Authenticate user from token
    user: Optional[AuthenticatedUser] = None
    if token:
        try:
            async for db in get_db():
                user = await get_current_active_user_from_token(token, db)
                break
        except Exception as e:
            logger.error(f"Authentication failed for websocket: {e}")
            await ws_manager.send_error(conversation_id, "Authentication failed")
            return

    if not user:
        await ws_manager.send_error(conversation_id, "Authentication required")
        return

    try:
        # Services use lazy sessions - no need to manage db connections here
        conversation_service = ConversationService()

        # Verify conversation exists or create it
        conversation = await conversation_service.get_conversation(
            conversation_id, user.company_id
        )
        if not conversation:
            # For simplicity, create a new conversation if it doesn't exist
            conversation_data = ConversationCreate(
                title=f"Chat Session {conversation_id}"
            )
            conversation = await conversation_service.create_conversation(
                conversation_data, user.company_id
            )
            logger.info(f"Created new conversation {conversation.id}")

        # Send initial connection confirmation
        connected_response = ConnectedResponse(
            conversation_id=conversation.id, title=conversation.title
        )
        await ws_manager.send_message(conversation_id, connected_response)

        while True:
            # Wait for message from client
            data = await websocket.receive_text()

            # Parse the message using our schemas
            client_message = parse_client_message(data)

            if client_message is None:
                await ws_manager.send_error(conversation_id, "Invalid message format")
                continue

            if isinstance(client_message, UserMessageRequest):
                await handle_user_message(
                    client_message,
                    conversation,
                    conversation_id,
                    ws_manager,
                    user,
                )

            elif isinstance(client_message, GetHistoryRequest):
                await handle_get_history(
                    conversation, conversation_id, ws_manager, user
                )

            elif isinstance(client_message, PingRequest):
                pong_response = PongResponse()
                await ws_manager.send_message(conversation_id, pong_response)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for conversation {conversation_id}")
    except Exception as e:
        logger.error(f"WebSocket error for conversation {conversation_id}: {e}")
        await ws_manager.send_error(conversation_id, f"Server error: {str(e)}")
    finally:
        ws_manager.disconnect(conversation_id)


async def handle_user_message(
    message: UserMessageRequest,
    conversation,
    conversation_id: int,
    ws_manager: WebSocketManager,
    user: AuthenticatedUser,
):
    """Handle a user message request."""
    user_content = message.content.strip()

    if not user_content:
        await ws_manager.send_error(conversation_id, "Empty message")
        return

    logger.info(f"Processing user message via WebSocket: {user_content}")
    logger.info(f"Permission mode: {message.permission_mode}")

    # Send acknowledgment that we received the message
    received_response = MessageReceivedResponse(content=user_content)
    await ws_manager.send_message(conversation_id, received_response)

    try:
        # Define callback to send messages as they're generated
        async def message_stream_callback(msg):
            agent_msg_response = AgentMessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                tool_calls=msg.tool_calls,
                tool_call_id=msg.tool_call_id,
                permission_mode=msg.permission_mode,
                sequence_number=msg.sequence_number,
                created_at=msg.created_at,
            )
            await ws_manager.send_message(conversation_id, agent_msg_response)

        # Agent service uses lazy sessions - no need to manage db connections
        agent_service = AgentService()

        # Process message with streaming callback, passing permission mode
        generated_messages = await agent_service.process_user_message(
            conversation.id,
            user_content,
            user,
            permission_mode=message.permission_mode,
            extra_data=message.extra_data,
            message_callback=message_stream_callback,
        )

        # Send completion signal
        complete_response = ResponseCompleteResponse()
        await ws_manager.send_message(conversation_id, complete_response)

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await ws_manager.send_error(
            conversation_id, f"Error processing message: {str(e)}"
        )


async def handle_get_history(
    conversation,
    conversation_id: int,
    ws_manager: WebSocketManager,
    user: AuthenticatedUser,
):
    """Handle a get history request."""
    try:
        # Conversation service uses lazy sessions
        conversation_service = ConversationService()
        messages = await conversation_service.get_conversation_messages(
            conversation.id, None, user.company_id
        )

        # Convert messages to response format
        message_responses = [
            AgentMessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                tool_calls=msg.tool_calls,
                tool_call_id=msg.tool_call_id,
                permission_mode=msg.permission_mode,
                sequence_number=msg.sequence_number,
                created_at=msg.created_at,
            )
            for msg in messages
        ]

        history_response = ConversationHistoryResponse(messages=message_responses)
        await ws_manager.send_message(conversation_id, history_response)

    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        await ws_manager.send_error(conversation_id, f"Error getting history: {str(e)}")
