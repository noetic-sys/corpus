import json
import os
from functools import lru_cache
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from common.providers.ai import AnthropicProvider
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.agents.services.conversation_service import ConversationService
from packages.agents.services.tool_service import ToolService
from packages.agents.models.domain.message import MessageModel
from packages.agents.models.schemas.message import MessageCreate
from common.providers.ai.interface import AIProviderInterface
from common.providers.ai.models import (
    Message,
    ChatCompletionMessageToolCall,
    InputMessage,
    MessageRole,
)
from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.agents.tools.base import ToolResult, ToolPermission

logger = get_logger(__name__)


class AgentService:
    """Service for running multi-step agent conversations with tool calling."""

    def __init__(
        self,
        db_session: AsyncSession,
        ai_provider: Optional[AIProviderInterface] = None,
    ):
        self.db_session = db_session
        self.conversation_service = ConversationService(db_session)
        self.tool_service = ToolService(db_session)

        # Default AI provider - could be configurable per conversation
        self.ai_provider = ai_provider or AnthropicProvider()

        # Set up prompts directory path
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        )
        self.prompts_dir = os.path.join(project_root, "prompts")

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

        Args:
            conversation_id: The conversation ID to process the message for
            user_message: The user's message content
            user: The authenticated user making the request
            permission_mode: Permission level for this message (READ or WRITE)
            extra_data: Additional message metadata (e.g., page context)
            max_iterations: Maximum number of agent iterations
            message_callback: Optional callback function called with each generated message as it's created
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

        generated_messages = []
        iteration = 0

        while iteration < max_iterations:
            logger.info(f"Agent iteration {iteration + 1}")

            # Get conversation history for context
            messages = await self.conversation_service.get_conversation_messages(
                conversation_id, None, user.company_id
            )

            # Prepare messages for AI provider
            ai_messages = self._prepare_messages_for_ai(messages)

            # Get tools in OpenAI format filtered by permission mode
            tools = self.tool_service.format_tools_for_openai(
                permission=permission_mode
            )

            # Call AI provider with tools
            try:
                response = await self._call_ai_with_tools(ai_messages, tools)

                # Parse response and check for tool calls
                assistant_message, tool_calls = self._parse_ai_response(response)

                # Add assistant message
                assistant_msg_data = MessageCreate(
                    role="assistant", content=assistant_message, tool_calls=tool_calls
                )
                assistant_msg = await self.conversation_service.add_message(
                    assistant_msg_data, conversation_id, user.company_id
                )
                generated_messages.append(assistant_msg)

                # Call callback immediately with new message if provided
                if message_callback:
                    await message_callback(assistant_msg)

                # If no tool calls, we're done
                if not tool_calls:
                    break

                # Execute tool calls and add tool responses
                for tool_call in tool_calls:
                    tool_result = await self.tool_service.execute_tool(
                        tool_call.function.name,
                        json.loads(tool_call.function.arguments),
                        user,
                    )

                    # Format tool result for response
                    tool_response = self._format_tool_result(tool_result)

                    # Add tool response message
                    tool_msg_data = MessageCreate(
                        role="tool", content=tool_response, tool_call_id=tool_call.id
                    )
                    tool_msg = await self.conversation_service.add_message(
                        tool_msg_data, conversation_id, user.company_id
                    )
                    generated_messages.append(tool_msg)

                    # Call callback immediately with new message if provided
                    if message_callback:
                        await message_callback(tool_msg)

                iteration += 1

            except Exception as e:
                logger.error(f"Error in agent iteration {iteration + 1}: {e}")
                # Add error message
                error_msg_data = MessageCreate(
                    role="assistant", content=f"I encountered an error: {str(e)}"
                )
                error_msg = await self.conversation_service.add_message(
                    error_msg_data, conversation_id, user.company_id
                )
                generated_messages.append(error_msg)

                # Call callback immediately with new message if provided
                if message_callback:
                    await message_callback(error_msg)
                break

        if iteration >= max_iterations:
            logger.warning(
                f"Agent reached max iterations ({max_iterations}) for conversation {conversation_id}"
            )

        return generated_messages

    def _prepare_messages_for_ai(
        self, messages: List[MessageModel]
    ) -> List[InputMessage]:
        """Convert stored messages to format expected by AI provider."""
        ai_messages = []

        for msg in messages:
            content = msg.content

            # For user messages with extra_data, append it to content
            if msg.role == "user" and msg.extra_data:
                context_str = f"\n\nExtra context: {json.dumps(msg.extra_data)}"
                content = f"{content}{context_str}" if content else context_str.strip()

            # Convert string role to MessageRole enum
            role = MessageRole(msg.role)

            # Create InputMessage with all fields
            ai_message = InputMessage(
                role=role,
                content=content or "",
                tool_calls=msg.tool_calls,
                tool_call_id=msg.tool_call_id,
            )
            ai_messages.append(ai_message)

        return ai_messages

    async def _call_ai_with_tools(
        self, messages: List[InputMessage], tools: List[Dict[str, Any]]
    ) -> Message:
        """Call AI provider with tool support."""
        # Add system message if not present
        if not messages or messages[0].role != MessageRole.SYSTEM:
            system_prompt = self._load_system_prompt()
            system_message = InputMessage(
                role=MessageRole.SYSTEM, content=system_prompt
            )
            messages = [system_message] + messages

        return await self.ai_provider.send_messages(messages, tools)

    @lru_cache(maxsize=1)
    def _load_system_prompt(self) -> str:
        """Load the agent system prompt from file with memory caching."""
        try:
            filepath = os.path.join(self.prompts_dir, "agent_system.txt")
            with open(filepath, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning("Agent system prompt file not found, using default")
            return "You are a helpful assistant that can call tools to help users. When you need to use a tool to answer a question, call the appropriate function."

    def _parse_ai_response(
        self, response: Message
    ) -> tuple[str, List[ChatCompletionMessageToolCall]]:
        """Parse AI response for tool calls."""
        content = response.content or ""
        tool_calls = response.tool_calls or []
        return content, tool_calls

    def _format_tool_result(self, tool_result: ToolResult) -> str:
        """Format tool execution result for AI consumption."""
        if tool_result.error:
            # Each tool's error result class has its own fields, so serialize the whole object
            try:
                error_dict = tool_result.error.model_dump()
                return f"Tool execution failed: {json.dumps(error_dict, default=str, indent=2)}"
            except Exception:
                # Fallback to string representation if serialization fails
                return f"Tool execution failed: {str(tool_result.error)}"
        elif tool_result.result:
            # Convert result to JSON string
            return json.dumps(tool_result.result.model_dump(), default=str, indent=2)
        else:
            return "Tool executed successfully with no result"


def get_agent_service(
    db_session: AsyncSession, ai_provider: Optional[AIProviderInterface] = None
) -> AgentService:
    """Get agent service instance."""
    return AgentService(db_session, ai_provider)
