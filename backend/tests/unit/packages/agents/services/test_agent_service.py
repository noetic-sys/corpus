import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from packages.agents.services.agent_service import AgentService, get_agent_service
from packages.agents.models.domain.message import MessageModel
from packages.agents.tools.base import ToolResult, ToolSuccessResult, ToolErrorResult
from common.providers.ai.models import (
    Message,
    ChatCompletionMessageToolCall,
    Function,
    InputMessage,
    MessageRole,
)
from packages.auth.models.domain.authenticated_user import AuthenticatedUser


class MockToolResult(ToolSuccessResult):
    result: str


class MockToolErrorResult(ToolErrorResult):
    error: str


class TestAgentService:
    """Test AgentService functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return AuthenticatedUser(company_id=1, user_id=1)

    @pytest.fixture
    def mock_ai_provider(self):
        """Create mock AI provider."""
        return AsyncMock()

    @pytest.fixture
    def agent_service(self, mock_session, mock_ai_provider):
        """Create agent service instance."""
        return AgentService(mock_session, mock_ai_provider)

    def test_agent_service_initialization(self, mock_session):
        """Test agent service initialization."""
        service = AgentService(mock_session)

        assert service.db_session == mock_session
        assert service.conversation_service is not None
        assert service.tool_service is not None
        assert service.ai_provider is not None

    def test_agent_service_initialization_with_custom_provider(
        self, mock_session, mock_ai_provider
    ):
        """Test agent service initialization with custom AI provider."""
        service = AgentService(mock_session, mock_ai_provider)

        assert service.db_session == mock_session
        assert service.ai_provider == mock_ai_provider

    def test_get_agent_service_function(self, mock_session):
        """Test get_agent_service factory function."""
        service = get_agent_service(mock_session)

        assert isinstance(service, AgentService)
        assert service.db_session == mock_session

    async def test_process_user_message_no_tools(
        self, agent_service, mock_session, mock_user
    ):
        """Test processing user message with no tool calls."""
        # Mock conversation service methods
        user_message = MessageModel(
            id=1,
            company_id=234,
            conversation_id=123,
            role="user",
            content="Hello, how are you?",
            sequence_number=1,
            tool_calls=None,
            tool_call_id=None,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00",
        )

        assistant_message = MessageModel(
            id=2,
            company_id=234,
            conversation_id=123,
            role="assistant",
            content="I'm doing well, thank you!",
            sequence_number=2,
            tool_calls=None,
            tool_call_id=None,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00",
        )

        # Mock AI response without tool calls
        ai_response = Message(content="I'm doing well, thank you!", tool_calls=None)

        with patch.object(
            agent_service.conversation_service, "add_message"
        ) as mock_add_message, patch.object(
            agent_service.conversation_service, "get_conversation_messages"
        ) as mock_get_messages, patch.object(
            agent_service.tool_service, "format_tools_for_openai"
        ) as mock_format_tools, patch.object(
            agent_service, "_call_ai_with_tools"
        ) as mock_call_ai:

            # Setup mocks
            mock_add_message.side_effect = [user_message, assistant_message]
            mock_get_messages.return_value = [user_message]
            mock_format_tools.return_value = []
            mock_call_ai.return_value = ai_response

            # Execute
            result = await agent_service.process_user_message(
                123, "Hello, how are you?", mock_user
            )

            # Verify
            assert len(result) == 1
            assert result[0] == assistant_message

            # Verify method calls
            assert mock_add_message.call_count == 2
            mock_get_messages.assert_called_once_with(123, None, mock_user.company_id)
            mock_format_tools.assert_called_once()
            mock_call_ai.assert_called_once()

    async def test_process_user_message_with_tool_calls(
        self, agent_service, mock_session, mock_user
    ):
        """Test processing user message with tool calls."""
        # Mock messages
        user_message = MessageModel(
            id=1,
            company_id=234,
            conversation_id=123,
            role="user",
            content="What's the weather like?",
            sequence_number=1,
            tool_calls=None,
            tool_call_id=None,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00",
        )

        # Mock tool call
        tool_call = ChatCompletionMessageToolCall(
            id="call_123",
            type="function",
            function=Function(name="get_weather", arguments='{"location": "New York"}'),
        )

        assistant_message = MessageModel(
            id=2,
            company_id=234,
            conversation_id=123,
            role="assistant",
            content="I'll check the weather for you.",
            sequence_number=2,
            tool_calls=[tool_call],
            tool_call_id=None,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00",
        )

        tool_message = MessageModel(
            id=3,
            company_id=234,
            conversation_id=123,
            role="tool",
            content='{"temperature": 72, "condition": "sunny"}',
            sequence_number=3,
            tool_calls=None,
            tool_call_id="call_123",
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00",
        )

        final_assistant_message = MessageModel(
            id=4,
            company_id=234,
            conversation_id=123,
            role="assistant",
            content="The weather is 72°F and sunny!",
            sequence_number=4,
            tool_calls=None,
            tool_call_id=None,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00",
        )

        # Mock AI responses
        ai_response_with_tool = Message(
            content="I'll check the weather for you.", tool_calls=[tool_call]
        )

        ai_response_final = Message(
            content="The weather is 72°F and sunny!", tool_calls=None
        )

        # Mock tool result
        mock_tool_result = ToolResult.ok(
            MockToolResult(result='{"temperature": 72, "condition": "sunny"}')
        )

        with patch.object(
            agent_service.conversation_service, "add_message"
        ) as mock_add_message, patch.object(
            agent_service.conversation_service, "get_conversation_messages"
        ) as mock_get_messages, patch.object(
            agent_service.tool_service, "format_tools_for_openai"
        ) as mock_format_tools, patch.object(
            agent_service.tool_service, "execute_tool"
        ) as mock_execute_tool, patch.object(
            agent_service, "_call_ai_with_tools"
        ) as mock_call_ai:

            # Setup mocks
            mock_add_message.side_effect = [
                user_message,
                assistant_message,
                tool_message,
                final_assistant_message,
            ]
            mock_get_messages.side_effect = [
                [user_message],  # First iteration
                [user_message, assistant_message, tool_message],  # Second iteration
            ]
            mock_format_tools.return_value = []
            mock_execute_tool.return_value = mock_tool_result
            mock_call_ai.side_effect = [ai_response_with_tool, ai_response_final]

            # Execute
            result = await agent_service.process_user_message(
                123, "What's the weather like?", mock_user
            )

            # Verify
            assert len(result) == 3  # assistant + tool + final assistant
            assert result[0] == assistant_message
            assert result[1] == tool_message
            assert result[2] == final_assistant_message

            # Verify tool was executed
            mock_execute_tool.assert_called_once_with(
                "get_weather", {"location": "New York"}, mock_user
            )

    async def test_process_user_message_tool_error(
        self, agent_service, mock_session, mock_user
    ):
        """Test processing user message when tool execution fails."""
        user_message = MessageModel(
            id=1,
            company_id=234,
            conversation_id=123,
            role="user",
            content="Check the database",
            sequence_number=1,
            tool_calls=None,
            tool_call_id=None,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00",
        )

        # Mock tool call
        tool_call = ChatCompletionMessageToolCall(
            id="call_456",
            type="function",
            function=Function(
                name="query_database", arguments='{"query": "SELECT * FROM users"}'
            ),
        )

        assistant_message = MessageModel(
            id=2,
            company_id=234,
            conversation_id=123,
            role="assistant",
            content="I'll query the database.",
            sequence_number=2,
            tool_calls=[tool_call],
            tool_call_id=None,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00",
        )

        tool_message = MessageModel(
            id=3,
            company_id=234,
            conversation_id=123,
            role="tool",
            content="Tool execution failed: Database connection failed",
            sequence_number=3,
            tool_calls=None,
            tool_call_id="call_456",
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00",
        )

        final_assistant_message = MessageModel(
            id=4,
            company_id=234,
            conversation_id=123,
            role="assistant",
            content="I'm sorry, I couldn't access the database.",
            sequence_number=4,
            tool_calls=None,
            tool_call_id=None,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00",
        )

        # Mock AI responses
        ai_response_with_tool = Message(
            content="I'll query the database.", tool_calls=[tool_call]
        )

        ai_response_final = Message(
            content="I'm sorry, I couldn't access the database.", tool_calls=None
        )

        # Mock tool error result
        mock_tool_result = ToolResult.err(
            MockToolErrorResult(error="Database connection failed")
        )

        with patch.object(
            agent_service.conversation_service, "add_message"
        ) as mock_add_message, patch.object(
            agent_service.conversation_service, "get_conversation_messages"
        ) as mock_get_messages, patch.object(
            agent_service.tool_service, "format_tools_for_openai"
        ) as mock_format_tools, patch.object(
            agent_service.tool_service, "execute_tool"
        ) as mock_execute_tool, patch.object(
            agent_service, "_call_ai_with_tools"
        ) as mock_call_ai:

            # Setup mocks
            mock_add_message.side_effect = [
                user_message,
                assistant_message,
                tool_message,
                final_assistant_message,
            ]
            mock_get_messages.side_effect = [
                [user_message],
                [user_message, assistant_message, tool_message],
            ]
            mock_format_tools.return_value = []
            mock_execute_tool.return_value = mock_tool_result
            mock_call_ai.side_effect = [ai_response_with_tool, ai_response_final]

            # Execute
            result = await agent_service.process_user_message(
                123, "Check the database", mock_user
            )

            # Verify tool error was handled
            assert len(result) == 3
            assert (
                result[1].content == "Tool execution failed: Database connection failed"
            )

    async def test_process_user_message_max_iterations(
        self, agent_service, mock_session, mock_user
    ):
        """Test that agent respects max iterations limit."""
        user_message = MessageModel(
            id=1,
            company_id=234,
            conversation_id=123,
            role="user",
            content="Keep calling tools",
            sequence_number=1,
            tool_calls=None,
            tool_call_id=None,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00",
        )

        # Mock tool call that keeps getting called
        tool_call = ChatCompletionMessageToolCall(
            id="call_loop",
            type="function",
            function=Function(name="endless_tool", arguments='{"param": "value"}'),
        )

        # AI always responds with tool calls
        ai_response_with_tool = Message(
            content="Calling tool again...", tool_calls=[tool_call]
        )

        # Mock tool result
        mock_tool_result = ToolResult.ok(MockToolResult(result="Tool executed"))

        with patch.object(
            agent_service.conversation_service, "add_message"
        ) as mock_add_message, patch.object(
            agent_service.conversation_service, "get_conversation_messages"
        ) as mock_get_messages, patch.object(
            agent_service.tool_service, "format_tools_for_openai"
        ) as mock_format_tools, patch.object(
            agent_service.tool_service, "execute_tool"
        ) as mock_execute_tool, patch.object(
            agent_service, "_call_ai_with_tools"
        ) as mock_call_ai:

            # Setup mocks - AI always returns tool calls
            mock_add_message.return_value = MagicMock()
            mock_get_messages.return_value = [user_message]
            mock_format_tools.return_value = []
            mock_execute_tool.return_value = mock_tool_result
            mock_call_ai.return_value = ai_response_with_tool

            # Execute with max_iterations=2
            result = await agent_service.process_user_message(
                123, "Keep calling tools", mock_user, max_iterations=2
            )

            # Should have stopped after 2 iterations
            # Each iteration adds assistant + tool message = 4 messages total
            assert len(result) == 4
            assert mock_call_ai.call_count == 2

    async def test_process_user_message_ai_exception(
        self, agent_service, mock_session, mock_user
    ):
        """Test handling of AI provider exceptions."""
        user_message = MessageModel(
            id=1,
            company_id=234,
            conversation_id=123,
            role="user",
            content="Hello",
            sequence_number=1,
            tool_calls=None,
            tool_call_id=None,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00",
        )

        error_message = MessageModel(
            id=2,
            company_id=234,
            conversation_id=123,
            role="assistant",
            content="I encountered an error: AI provider failed",
            sequence_number=2,
            tool_calls=None,
            tool_call_id=None,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00",
        )

        with patch.object(
            agent_service.conversation_service, "add_message"
        ) as mock_add_message, patch.object(
            agent_service.conversation_service, "get_conversation_messages"
        ) as mock_get_messages, patch.object(
            agent_service.tool_service, "format_tools_for_openai"
        ) as mock_format_tools, patch.object(
            agent_service, "_call_ai_with_tools"
        ) as mock_call_ai:

            # Setup mocks
            mock_add_message.side_effect = [user_message, error_message]
            mock_get_messages.return_value = [user_message]
            mock_format_tools.return_value = []
            mock_call_ai.side_effect = Exception("AI provider failed")

            # Execute
            result = await agent_service.process_user_message(123, "Hello", mock_user)

            # Verify error was handled
            assert len(result) == 1
            assert result[0] == error_message
            assert "I encountered an error: AI provider failed" in result[0].content

    def test_prepare_messages_for_ai(self, agent_service):
        """Test message preparation for AI provider."""
        messages = [
            MessageModel(
                id=1,
                company_id=234,
                conversation_id=123,
                role="user",
                content="Hello",
                sequence_number=1,
                tool_calls=None,
                tool_call_id=None,
                created_at="2023-01-01T00:00:00",
                updated_at="2023-01-01T00:00:00",
            ),
            MessageModel(
                id=2,
                company_id=234,
                conversation_id=123,
                role="assistant",
                content="I'll help you",
                sequence_number=2,
                tool_calls=[
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"location": "NYC"}',
                        },
                    }
                ],
                tool_call_id=None,
                created_at="2023-01-01T00:00:00",
                updated_at="2023-01-01T00:00:00",
            ),
            MessageModel(
                id=3,
                company_id=234,
                conversation_id=123,
                role="tool",
                content="Weather data",
                sequence_number=3,
                tool_calls=None,
                tool_call_id="call_123",
                created_at="2023-01-01T00:00:00",
                updated_at="2023-01-01T00:00:00",
            ),
        ]

        result = agent_service._prepare_messages_for_ai(messages)

        # Verify structure - now returns InputMessage objects
        assert len(result) == 3
        assert isinstance(result[0], InputMessage)
        assert result[0].role == MessageRole.USER
        assert result[0].content == "Hello"

        assert isinstance(result[1], InputMessage)
        assert result[1].role == MessageRole.ASSISTANT
        assert result[1].tool_calls is not None

        assert isinstance(result[2], InputMessage)
        assert result[2].role == MessageRole.TOOL
        assert result[2].tool_call_id == "call_123"

    async def test_call_ai_with_tools_adds_system_message(self, agent_service):
        """Test that system message is added when not present."""
        messages = [InputMessage(role=MessageRole.USER, content="Hello")]
        tools = []

        # Mock AI response
        mock_response = Message(content="Response", tool_calls=None)
        with patch.object(
            agent_service.ai_provider, "send_messages", return_value=mock_response
        ) as mock_send:
            result = await agent_service._call_ai_with_tools(messages, tools)

            # Verify system message was added
            called_messages = mock_send.call_args[0][0]
            assert len(called_messages) == 2
            assert isinstance(called_messages[0], InputMessage)
            assert called_messages[0].role == MessageRole.SYSTEM
            # Updated to match actual system prompt content
            assert "Corpus" in called_messages[0].content
            assert called_messages[1].role == MessageRole.USER

    async def test_call_ai_with_tools_preserves_system_message(self, agent_service):
        """Test that existing system message is preserved."""
        messages = [
            InputMessage(role=MessageRole.SYSTEM, content="Custom system message"),
            InputMessage(role=MessageRole.USER, content="Hello"),
        ]
        tools = []

        # Mock AI response
        mock_response = Message(content="Response", tool_calls=None)
        with patch.object(
            agent_service.ai_provider, "send_messages", return_value=mock_response
        ) as mock_send:
            result = await agent_service._call_ai_with_tools(messages, tools)

            # Verify system message was preserved
            called_messages = mock_send.call_args[0][0]
            assert len(called_messages) == 2
            assert isinstance(called_messages[0], InputMessage)
            assert called_messages[0].role == MessageRole.SYSTEM
            assert called_messages[0].content == "Custom system message"

    def test_parse_ai_response(self, agent_service):
        """Test AI response parsing."""
        tool_call = ChatCompletionMessageToolCall(
            id="call_123",
            type="function",
            function=Function(name="test_tool", arguments='{"arg": "value"}'),
        )

        # Test with content and tool calls
        response = Message(content="I'll help you", tool_calls=[tool_call])
        content, tool_calls_result = agent_service._parse_ai_response(response)

        assert content == "I'll help you"
        assert len(tool_calls_result) == 1
        assert tool_calls_result[0].id == "call_123"

        # Test with no content
        response_no_content = Message(content=None, tool_calls=[])
        content, tool_calls_result = agent_service._parse_ai_response(
            response_no_content
        )

        assert content == ""
        assert len(tool_calls_result) == 0

    def test_format_tool_result_success(self, agent_service):
        """Test formatting successful tool results."""
        mock_result = MockToolResult(result="Success result")
        tool_result = ToolResult.ok(mock_result)

        formatted = agent_service._format_tool_result(tool_result)

        # Should be JSON formatted
        parsed = json.loads(formatted)
        assert parsed["result"] == "Success result"

    def test_format_tool_result_error(self, agent_service):
        """Test formatting error tool results."""
        mock_error = MockToolErrorResult(error="Tool failed")
        tool_result = ToolResult.err(mock_error)

        formatted = agent_service._format_tool_result(tool_result)

        # The service now formats errors as JSON, so check for JSON structure
        assert "Tool execution failed:" in formatted
        assert "Tool failed" in formatted

    def test_format_tool_result_no_result(self, agent_service):
        """Test formatting tool result with no data."""
        tool_result = ToolResult(result=None, error=None)

        formatted = agent_service._format_tool_result(tool_result)

        assert formatted == "Tool executed successfully with no result"
