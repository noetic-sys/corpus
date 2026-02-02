import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Set

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    UserPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)

from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.agents.services.conversation_service import ConversationService
from packages.agents.services.pydantic_ai_runner import PydanticAIRunner
from packages.agents.models.domain.message import MessageModel
from packages.agents.models.domain.agent_dependencies import AgentDependencies
from packages.agents.models.schemas.message import MessageCreate
from common.providers.ai.models import ChatCompletionMessageToolCall, Function
from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.agents.tools.base import ToolPermission

logger = get_logger(__name__)


class AgentService:
    """Service for running multi-step agent conversations with tool calling.

    Uses PydanticAI for the agent loop with parallel tool execution and streaming.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.conversation_service = ConversationService()
        self.runner = PydanticAIRunner(model_name)

    @trace_span
    async def process_user_message(
        self,
        conversation_id: int,
        user_message: str,
        user: AuthenticatedUser,
        permission_mode: ToolPermission = ToolPermission.READ,
        extra_data: Optional[Dict[str, Any]] = None,
        max_iterations: int = 20,
        message_callback=None,
    ) -> List[MessageModel]:
        """Process a user message and return all messages generated in the conversation turn.

        Uses PydanticAI for the agent loop with parallel tool execution.
        Streams tool execution events in real-time via callbacks.

        Args:
            conversation_id: The conversation ID to process the message for
            user_message: The user's message content
            user: The authenticated user making the request
            permission_mode: Permission level for this message (READ or WRITE)
            extra_data: Additional message metadata (e.g., page context)
            max_iterations: Maximum number of agent iterations (used by PydanticAI)
            message_callback: Optional callback function called with each generated message
        """
        logger.info(f"Processing user message in conversation {conversation_id}")
        logger.info(f"Authed user: {user}")
        logger.info(f"Using permission mode: {permission_mode}")

        # Add user message to conversation
        user_msg = await self.conversation_service.add_message(
            MessageCreate(
                role="user",
                content=user_message,
                permission_mode=permission_mode,
                extra_data=extra_data,
            ),
            conversation_id,
            user.company_id,
        )

        # Get existing conversation history
        existing_messages = await self.conversation_service.get_conversation_messages(
            conversation_id, None, user.company_id
        )

        # Convert to PydanticAI message format
        pydantic_ai_history = self._convert_to_pydantic_ai_messages(existing_messages)

        # Track streamed tool call IDs to avoid duplicate persistence
        streamed_tool_call_ids: Set[str] = set()
        sequence_counter = len(existing_messages)

        # Create streaming callbacks for real-time tool execution visibility
        async def on_tool_start(tool_name: str, tool_call_id: str, args: dict):
            """Called when a tool starts executing - send preview message."""
            nonlocal sequence_counter
            if message_callback:
                sequence_counter += 1
                # Create a preview assistant message showing the tool call
                preview_msg = MessageModel(
                    id=-1,  # Temporary ID for preview
                    company_id=user.company_id,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=None,
                    tool_calls=[
                        ChatCompletionMessageToolCall(
                            id=tool_call_id,
                            type="function",
                            function=Function(
                                name=tool_name,
                                arguments=json.dumps(args),
                            ),
                        )
                    ],
                    tool_call_id=None,
                    permission_mode=permission_mode,
                    sequence_number=sequence_counter,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                streamed_tool_call_ids.add(tool_call_id)
                await message_callback(preview_msg)
                logger.info(f"Streamed tool start: {tool_name} ({tool_call_id})")

        async def on_tool_result(tool_name: str, tool_call_id: str, result: str):
            """Called when a tool completes - send preview result message."""
            nonlocal sequence_counter
            if message_callback:
                sequence_counter += 1
                # Create a preview tool result message
                preview_msg = MessageModel(
                    id=-1,  # Temporary ID for preview
                    company_id=user.company_id,
                    conversation_id=conversation_id,
                    role="tool",
                    content=result,
                    tool_calls=None,
                    tool_call_id=tool_call_id,
                    permission_mode=permission_mode,
                    sequence_number=sequence_counter,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                await message_callback(preview_msg)
                logger.info(f"Streamed tool result: {tool_name} ({tool_call_id})")

        # Prepare dependencies with streaming callbacks
        deps = AgentDependencies(
            user=user,
            conversation_id=conversation_id,
            permission_mode=permission_mode,
            extra_data=extra_data,
            on_tool_start=on_tool_start if message_callback else None,
            on_tool_result=on_tool_result if message_callback else None,
        )

        generated_messages: List[MessageModel] = []

        try:
            # Run agent with PydanticAI
            # Note: user_message is empty string since it's already in history
            final_response, all_messages = await self.runner.run(
                user_message="",  # Message already in history
                deps=deps,
                message_history=pydantic_ai_history,
            )

            # Extract new messages (those not in original history)
            new_messages = all_messages[len(pydantic_ai_history):]

            # Convert and persist new messages
            # Tool calls/results were already streamed, but we still persist them
            for pydantic_msg in new_messages:
                persisted_msgs = await self._persist_pydantic_ai_message(
                    pydantic_msg, conversation_id, user.company_id
                )

                for msg in persisted_msgs:
                    generated_messages.append(msg)
                    # Only callback for messages that weren't already streamed
                    # (final assistant response text)
                    if message_callback:
                        is_streamed_tool_call = (
                            msg.role == "assistant"
                            and msg.tool_calls
                            and any(tc.id in streamed_tool_call_ids for tc in msg.tool_calls)
                        )
                        is_streamed_tool_result = (
                            msg.role == "tool"
                            and msg.tool_call_id in streamed_tool_call_ids
                        )
                        if not is_streamed_tool_call and not is_streamed_tool_result:
                            await message_callback(msg)

        except Exception as e:
            logger.error(f"Error in PydanticAI agent: {e}")
            error_msg_data = MessageCreate(
                role="assistant", content=f"I encountered an error: {str(e)}"
            )
            error_msg = await self.conversation_service.add_message(
                error_msg_data, conversation_id, user.company_id
            )
            generated_messages.append(error_msg)

            if message_callback:
                await message_callback(error_msg)

        return generated_messages

    def _convert_to_pydantic_ai_messages(
        self, messages: List[MessageModel]
    ) -> List[ModelMessage]:
        """Convert our MessageModel list to PydanticAI ModelMessage format."""
        result: List[ModelMessage] = []

        i = 0
        while i < len(messages):
            msg = messages[i]

            if msg.role == "system":
                # System messages become part of request
                result.append(
                    ModelRequest(parts=[SystemPromptPart(content=msg.content or "")])
                )

            elif msg.role == "user":
                # User messages become ModelRequest with UserPromptPart
                content = msg.content or ""
                if msg.extra_data:
                    content += f"\n\nExtra context: {json.dumps(msg.extra_data)}"
                result.append(
                    ModelRequest(parts=[UserPromptPart(content=content)])
                )

            elif msg.role == "assistant":
                # Assistant messages become ModelResponse
                parts = []

                if msg.content:
                    parts.append(TextPart(content=msg.content))

                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        parts.append(
                            ToolCallPart(
                                tool_name=tc.function.name,
                                args=json.loads(tc.function.arguments),
                                tool_call_id=tc.id,
                            )
                        )

                if parts:
                    result.append(ModelResponse(parts=parts))

            elif msg.role == "tool":
                # Tool results - need to pair with previous request
                if msg.tool_call_id:
                    result.append(
                        ModelRequest(
                            parts=[
                                ToolReturnPart(
                                    tool_name="",  # Will be inferred
                                    content=msg.content or "",
                                    tool_call_id=msg.tool_call_id,
                                )
                            ]
                        )
                    )

            i += 1

        return result

    async def _persist_pydantic_ai_message(
        self,
        pydantic_msg: ModelMessage,
        conversation_id: int,
        company_id: int,
    ) -> List[MessageModel]:
        """Convert and persist a PydanticAI message to our database format."""
        persisted: List[MessageModel] = []

        if isinstance(pydantic_msg, ModelResponse):
            # Extract text content and tool calls
            text_content = ""
            tool_calls: List[ChatCompletionMessageToolCall] = []

            for part in pydantic_msg.parts:
                if isinstance(part, TextPart):
                    text_content += part.content
                elif isinstance(part, ToolCallPart):
                    tool_calls.append(
                        ChatCompletionMessageToolCall(
                            id=part.tool_call_id or "",
                            type="function",
                            function=Function(
                                name=part.tool_name,
                                arguments=json.dumps(part.args),
                            ),
                        )
                    )

            # Persist assistant message
            assistant_msg = await self.conversation_service.add_message(
                MessageCreate(
                    role="assistant",
                    content=text_content if text_content else None,
                    tool_calls=tool_calls if tool_calls else None,
                ),
                conversation_id,
                company_id,
            )
            persisted.append(assistant_msg)

        elif isinstance(pydantic_msg, ModelRequest):
            # Handle tool return parts
            for part in pydantic_msg.parts:
                if isinstance(part, ToolReturnPart):
                    tool_msg = await self.conversation_service.add_message(
                        MessageCreate(
                            role="tool",
                            content=part.content,
                            tool_call_id=part.tool_call_id,
                        ),
                        conversation_id,
                        company_id,
                    )
                    persisted.append(tool_msg)

        return persisted


def get_agent_service(model_name: Optional[str] = None) -> AgentService:
    """Factory function for AgentService."""
    return AgentService(model_name=model_name)
