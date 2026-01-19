import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    UserPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)

from packages.agents.services.agent_service import AgentService, get_agent_service
from packages.agents.models.domain.message import MessageModel
from packages.agents.tools.base import ToolPermission
from common.providers.ai.models import ChatCompletionMessageToolCall, Function
from packages.auth.models.domain.authenticated_user import AuthenticatedUser


class TestAgentService:
    """Test AgentService functionality."""

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return AuthenticatedUser(company_id=1, user_id=1)

    @pytest.fixture
    def agent_service(self):
        """Create agent service instance with mocked runner."""
        service = AgentService()
        service.runner = MagicMock()
        service.conversation_service = MagicMock()
        return service

    def test_agent_service_initialization(self):
        """Test agent service initialization."""
        with patch(
            "packages.agents.services.agent_service.PydanticAIRunner"
        ), patch(
            "packages.agents.services.agent_service.ConversationService"
        ):
            service = AgentService()
            assert service.conversation_service is not None
            assert service.runner is not None

    def test_agent_service_initialization_with_model_name(self):
        """Test agent service initialization with custom model name."""
        with patch(
            "packages.agents.services.agent_service.PydanticAIRunner"
        ) as mock_runner, patch(
            "packages.agents.services.agent_service.ConversationService"
        ):
            service = AgentService(model_name="claude-3-opus")
            mock_runner.assert_called_once_with("claude-3-opus")

    def test_get_agent_service_function(self):
        """Test get_agent_service factory function."""
        with patch(
            "packages.agents.services.agent_service.PydanticAIRunner"
        ), patch(
            "packages.agents.services.agent_service.ConversationService"
        ):
            service = get_agent_service()
            assert isinstance(service, AgentService)

    def test_convert_to_pydantic_ai_messages_user(self, agent_service):
        """Test conversion of user messages to PydanticAI format."""
        messages = [
            MessageModel(
                id=1,
                company_id=1,
                conversation_id=123,
                role="user",
                content="Hello, how are you?",
                sequence_number=1,
                tool_calls=None,
                tool_call_id=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        ]

        result = agent_service._convert_to_pydantic_ai_messages(messages)

        assert len(result) == 1
        assert isinstance(result[0], ModelRequest)
        assert len(result[0].parts) == 1
        assert isinstance(result[0].parts[0], UserPromptPart)
        assert result[0].parts[0].content == "Hello, how are you?"

    def test_convert_to_pydantic_ai_messages_user_with_extra_data(self, agent_service):
        """Test conversion of user messages with extra_data."""
        messages = [
            MessageModel(
                id=1,
                company_id=1,
                conversation_id=123,
                role="user",
                content="What's on this page?",
                sequence_number=1,
                tool_calls=None,
                tool_call_id=None,
                extra_data={"page_url": "https://example.com"},
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        ]

        result = agent_service._convert_to_pydantic_ai_messages(messages)

        assert len(result) == 1
        content = result[0].parts[0].content
        assert "What's on this page?" in content
        assert "Extra context:" in content
        assert "page_url" in content

    def test_convert_to_pydantic_ai_messages_assistant(self, agent_service):
        """Test conversion of assistant messages to PydanticAI format."""
        messages = [
            MessageModel(
                id=1,
                company_id=1,
                conversation_id=123,
                role="assistant",
                content="I'm doing well, thank you!",
                sequence_number=1,
                tool_calls=None,
                tool_call_id=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        ]

        result = agent_service._convert_to_pydantic_ai_messages(messages)

        assert len(result) == 1
        assert isinstance(result[0], ModelResponse)
        assert len(result[0].parts) == 1
        assert isinstance(result[0].parts[0], TextPart)
        assert result[0].parts[0].content == "I'm doing well, thank you!"

    def test_convert_to_pydantic_ai_messages_assistant_with_tool_calls(
        self, agent_service
    ):
        """Test conversion of assistant messages with tool calls."""
        tool_call = ChatCompletionMessageToolCall(
            id="call_123",
            type="function",
            function=Function(name="search", arguments='{"query": "test"}'),
        )

        messages = [
            MessageModel(
                id=1,
                company_id=1,
                conversation_id=123,
                role="assistant",
                content="Let me search for that.",
                sequence_number=1,
                tool_calls=[tool_call],
                tool_call_id=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        ]

        result = agent_service._convert_to_pydantic_ai_messages(messages)

        assert len(result) == 1
        assert isinstance(result[0], ModelResponse)
        assert len(result[0].parts) == 2
        assert isinstance(result[0].parts[0], TextPart)
        assert isinstance(result[0].parts[1], ToolCallPart)
        assert result[0].parts[1].tool_name == "search"
        assert result[0].parts[1].args == {"query": "test"}

    def test_convert_to_pydantic_ai_messages_tool_result(self, agent_service):
        """Test conversion of tool result messages."""
        messages = [
            MessageModel(
                id=1,
                company_id=1,
                conversation_id=123,
                role="tool",
                content='{"results": ["item1", "item2"]}',
                sequence_number=1,
                tool_calls=None,
                tool_call_id="call_123",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        ]

        result = agent_service._convert_to_pydantic_ai_messages(messages)

        assert len(result) == 1
        assert isinstance(result[0], ModelRequest)
        assert len(result[0].parts) == 1
        assert isinstance(result[0].parts[0], ToolReturnPart)
        assert result[0].parts[0].tool_call_id == "call_123"

    async def test_process_user_message_success(self, agent_service, mock_user):
        """Test successful processing of user message."""
        # Setup mocks
        user_msg = MessageModel(
            id=1,
            company_id=1,
            conversation_id=123,
            role="user",
            content="Hello",
            sequence_number=1,
            tool_calls=None,
            tool_call_id=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assistant_msg = MessageModel(
            id=2,
            company_id=1,
            conversation_id=123,
            role="assistant",
            content="Hi there!",
            sequence_number=2,
            tool_calls=None,
            tool_call_id=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Mock conversation service
        agent_service.conversation_service.add_message = AsyncMock(
            side_effect=[user_msg, assistant_msg]
        )
        agent_service.conversation_service.get_conversation_messages = AsyncMock(
            return_value=[user_msg]
        )

        # Mock runner to return a simple response
        response_message = ModelResponse(parts=[TextPart(content="Hi there!")])
        agent_service.runner.run = AsyncMock(
            return_value=("Hi there!", [ModelRequest(parts=[UserPromptPart(content="Hello")]), response_message])
        )

        # Execute
        result = await agent_service.process_user_message(
            conversation_id=123,
            user_message="Hello",
            user=mock_user,
        )

        # Verify
        assert len(result) == 1
        assert result[0].content == "Hi there!"

    async def test_process_user_message_with_callback(self, agent_service, mock_user):
        """Test that message callback is called for each generated message."""
        user_msg = MessageModel(
            id=1,
            company_id=1,
            conversation_id=123,
            role="user",
            content="Hello",
            sequence_number=1,
            tool_calls=None,
            tool_call_id=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assistant_msg = MessageModel(
            id=2,
            company_id=1,
            conversation_id=123,
            role="assistant",
            content="Hi there!",
            sequence_number=2,
            tool_calls=None,
            tool_call_id=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        agent_service.conversation_service.add_message = AsyncMock(
            side_effect=[user_msg, assistant_msg]
        )
        agent_service.conversation_service.get_conversation_messages = AsyncMock(
            return_value=[user_msg]
        )

        response_message = ModelResponse(parts=[TextPart(content="Hi there!")])
        agent_service.runner.run = AsyncMock(
            return_value=("Hi there!", [ModelRequest(parts=[UserPromptPart(content="Hello")]), response_message])
        )

        callback = AsyncMock()

        await agent_service.process_user_message(
            conversation_id=123,
            user_message="Hello",
            user=mock_user,
            message_callback=callback,
        )

        # Callback should be called for the assistant message
        callback.assert_called_once_with(assistant_msg)

    async def test_process_user_message_error_handling(self, agent_service, mock_user):
        """Test error handling in process_user_message."""
        user_msg = MessageModel(
            id=1,
            company_id=1,
            conversation_id=123,
            role="user",
            content="Hello",
            sequence_number=1,
            tool_calls=None,
            tool_call_id=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        error_msg = MessageModel(
            id=2,
            company_id=1,
            conversation_id=123,
            role="assistant",
            content="I encountered an error: Test error",
            sequence_number=2,
            tool_calls=None,
            tool_call_id=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        agent_service.conversation_service.add_message = AsyncMock(
            side_effect=[user_msg, error_msg]
        )
        agent_service.conversation_service.get_conversation_messages = AsyncMock(
            return_value=[user_msg]
        )

        # Runner raises an exception
        agent_service.runner.run = AsyncMock(side_effect=Exception("Test error"))

        result = await agent_service.process_user_message(
            conversation_id=123,
            user_message="Hello",
            user=mock_user,
        )

        assert len(result) == 1
        assert "I encountered an error: Test error" in result[0].content

    async def test_persist_pydantic_ai_message_response(self, agent_service):
        """Test persisting a ModelResponse message."""
        assistant_msg = MessageModel(
            id=1,
            company_id=1,
            conversation_id=123,
            role="assistant",
            content="Test response",
            sequence_number=1,
            tool_calls=None,
            tool_call_id=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        agent_service.conversation_service.add_message = AsyncMock(
            return_value=assistant_msg
        )

        pydantic_msg = ModelResponse(parts=[TextPart(content="Test response")])

        result = await agent_service._persist_pydantic_ai_message(
            pydantic_msg, conversation_id=123, company_id=1
        )

        assert len(result) == 1
        assert result[0] == assistant_msg

    async def test_persist_pydantic_ai_message_with_tool_calls(self, agent_service):
        """Test persisting a ModelResponse with tool calls."""
        assistant_msg = MessageModel(
            id=1,
            company_id=1,
            conversation_id=123,
            role="assistant",
            content="",
            sequence_number=1,
            tool_calls=[
                ChatCompletionMessageToolCall(
                    id="call_123",
                    type="function",
                    function=Function(name="search", arguments='{"query": "test"}'),
                )
            ],
            tool_call_id=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        agent_service.conversation_service.add_message = AsyncMock(
            return_value=assistant_msg
        )

        pydantic_msg = ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="search",
                    args={"query": "test"},
                    tool_call_id="call_123",
                )
            ]
        )

        result = await agent_service._persist_pydantic_ai_message(
            pydantic_msg, conversation_id=123, company_id=1
        )

        assert len(result) == 1
        # Verify add_message was called with correct tool_calls
        call_args = agent_service.conversation_service.add_message.call_args
        message_create = call_args[0][0]
        assert message_create.role == "assistant"
        assert len(message_create.tool_calls) == 1

    async def test_persist_pydantic_ai_message_tool_return(self, agent_service):
        """Test persisting a tool return message."""
        tool_msg = MessageModel(
            id=1,
            company_id=1,
            conversation_id=123,
            role="tool",
            content="Tool result",
            sequence_number=1,
            tool_calls=None,
            tool_call_id="call_123",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        agent_service.conversation_service.add_message = AsyncMock(
            return_value=tool_msg
        )

        pydantic_msg = ModelRequest(
            parts=[
                ToolReturnPart(
                    tool_name="search",
                    content="Tool result",
                    tool_call_id="call_123",
                )
            ]
        )

        result = await agent_service._persist_pydantic_ai_message(
            pydantic_msg, conversation_id=123, company_id=1
        )

        assert len(result) == 1
        assert result[0] == tool_msg
