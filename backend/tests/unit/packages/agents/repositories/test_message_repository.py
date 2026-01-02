import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from packages.agents.repositories.message_repository import MessageRepository
from packages.agents.models.database.message import MessageEntity
from packages.agents.models.database.conversation import ConversationEntity
from packages.agents.models.domain.message import MessageCreateModel, MessageUpdateModel


class TestMessageRepository:
    """Test MessageRepository methods."""

    @pytest.fixture
    async def repository(self, test_db: AsyncSession):
        """Create repository instance."""
        return MessageRepository(test_db)

    async def test_create_message_success(
        self, repository, sample_conversation, sample_company
    ):
        """Test successful message creation."""
        message_data = MessageCreateModel(
            conversation_id=sample_conversation.id,
            company_id=sample_company.id,
            role="user",
            content="Test message content",
            sequence_number=1,
            extra_data={"test_key": "test_value"},
        )

        result = await repository.create(message_data)

        assert result.conversation_id == sample_conversation.id
        assert result.role == "user"
        assert result.content == "Test message content"
        assert result.sequence_number == 1
        assert result.extra_data == {"test_key": "test_value"}
        assert result.id is not None

    async def test_create_message_minimal(
        self, repository, sample_conversation, sample_company
    ):
        """Test creating message with minimal data."""
        message_data = MessageCreateModel(
            conversation_id=sample_conversation.id,
            company_id=sample_company.id,
            role="assistant",
            content="Minimal message",
            sequence_number=1,
        )

        result = await repository.create(message_data)

        assert result.conversation_id == sample_conversation.id
        assert result.role == "assistant"
        assert result.content == "Minimal message"
        assert result.sequence_number == 1
        assert result.extra_data is None

    async def test_get_message_exists(self, repository, sample_message):
        """Test getting existing message."""
        result = await repository.get(sample_message.id)

        assert result is not None
        assert result.id == sample_message.id
        assert result.conversation_id == sample_message.conversation_id
        assert result.role == sample_message.role
        assert result.content == sample_message.content

    async def test_get_message_not_exists(self, repository):
        """Test getting non-existent message."""
        result = await repository.get(999)
        assert result is None

    async def test_update_message_success(self, repository, sample_message):
        """Test successful message update."""
        update_data = MessageUpdateModel(
            content="Updated message content",
            extra_data={"updated": True},
        )

        result = await repository.update(sample_message.id, update_data)

        assert result is not None
        assert result.content == "Updated message content"
        assert result.extra_data == {"updated": True}
        assert result.role == sample_message.role  # Unchanged

    async def test_update_message_partial(self, repository, sample_message):
        """Test partial message update."""
        update_data = MessageUpdateModel(content="Only content updated")

        result = await repository.update(sample_message.id, update_data)

        assert result is not None
        assert result.content == "Only content updated"
        assert result.role == sample_message.role  # Unchanged
        assert result.sequence_number == sample_message.sequence_number  # Unchanged

    async def test_update_message_not_found(self, repository):
        """Test updating non-existent message."""
        update_data = MessageUpdateModel(content="Updated")

        result = await repository.update(999, update_data)
        assert result is None

    async def test_delete_message_success(self, repository, sample_message):
        """Test successful message deletion."""
        success = await repository.delete(sample_message.id)
        assert success is True

        # Verify message is deleted
        result = await repository.get(sample_message.id)
        assert result is None

    async def test_delete_message_not_found(self, repository):
        """Test deleting non-existent message."""
        success = await repository.delete(999)
        assert success is False

    async def test_get_messages_for_conversation(
        self, repository, sample_conversation, sample_company
    ):
        """Test getting all messages for a conversation."""
        # Create multiple messages in conversation
        messages_data = [
            MessageCreateModel(
                conversation_id=sample_conversation.id,
                company_id=sample_company.id,
                role="user",
                content="First message",
                sequence_number=1,
            ),
            MessageCreateModel(
                conversation_id=sample_conversation.id,
                company_id=sample_company.id,
                role="assistant",
                content="Second message",
                sequence_number=2,
            ),
            MessageCreateModel(
                conversation_id=sample_conversation.id,
                company_id=sample_company.id,
                role="user",
                content="Third message",
                sequence_number=3,
            ),
        ]

        for data in messages_data:
            await repository.create(data)

        # Get messages for conversation
        results = await repository.get_by_conversation_id(sample_conversation.id)

        assert len(results) == 3
        # Should be ordered by sequence_number
        assert results[0].content == "First message"
        assert results[1].content == "Second message"
        assert results[2].content == "Third message"

    async def test_get_messages_for_conversation_empty(
        self, repository, sample_conversation
    ):
        """Test getting messages for conversation with no messages."""
        results = await repository.get_by_conversation_id(sample_conversation.id)
        assert len(results) == 0

    async def test_get_messages_for_conversation_different_conversations(
        self, repository, sample_ai_model, sample_company
    ):
        """Test that messages are filtered by conversation."""
        # Create two conversations
        conv1 = ConversationEntity(
            title="Conversation 1",
            ai_model_id=sample_ai_model.id,
            company_id=sample_company.id,
        )
        conv2 = ConversationEntity(
            title="Conversation 2",
            ai_model_id=sample_ai_model.id,
            company_id=sample_company.id,
        )
        repository.db_session.add_all([conv1, conv2])
        await repository.db_session.commit()
        await repository.db_session.refresh(conv1)
        await repository.db_session.refresh(conv2)

        # Create messages in both conversations
        msg1 = MessageEntity(
            conversation_id=conv1.id,
            company_id=sample_company.id,
            role="user",
            content="Message in conv1",
            sequence_number=1,
        )
        msg2 = MessageEntity(
            conversation_id=conv2.id,
            company_id=sample_company.id,
            role="user",
            content="Message in conv2",
            sequence_number=1,
        )
        msg3 = MessageEntity(
            conversation_id=conv1.id,
            company_id=sample_company.id,
            role="assistant",
            content="Another message in conv1",
            sequence_number=2,
        )

        repository.db_session.add_all([msg1, msg2, msg3])
        await repository.db_session.commit()

        # Get messages for first conversation only
        results = await repository.get_by_conversation_id(conv1.id)

        assert len(results) == 2
        contents = [msg.content for msg in results]
        assert "Message in conv1" in contents
        assert "Another message in conv1" in contents
        assert "Message in conv2" not in contents

    async def test_get_messages_ordered_by_sequence_number(
        self, repository, sample_conversation, sample_company
    ):
        """Test that messages are ordered by sequence_number."""
        # Create messages with non-sequential order values
        messages_data = [
            {
                "conversation_id": sample_conversation.id,
                "company_id": sample_company.id,
                "role": "user",
                "content": "Third in order",
                "sequence_number": 5,
            },
            {
                "conversation_id": sample_conversation.id,
                "company_id": sample_company.id,
                "role": "assistant",
                "content": "First in order",
                "sequence_number": 1,
            },
            {
                "conversation_id": sample_conversation.id,
                "company_id": sample_company.id,
                "role": "user",
                "content": "Second in order",
                "sequence_number": 3,
            },
        ]

        for data in messages_data:
            message = MessageEntity(**data)
            repository.db_session.add(message)

        await repository.db_session.commit()

        # Get messages - should be ordered by sequence_number
        results = await repository.get_by_conversation_id(sample_conversation.id)

        assert len(results) == 3
        assert results[0].content == "First in order"
        assert results[0].sequence_number == 1
        assert results[1].content == "Second in order"
        assert results[1].sequence_number == 3
        assert results[2].content == "Third in order"
        assert results[2].sequence_number == 5

    async def test_get_latest_messages_with_limit(
        self, repository, sample_conversation, sample_company
    ):
        """Test getting latest messages with limit."""
        # Create multiple messages
        for i in range(5):
            message = MessageEntity(
                conversation_id=sample_conversation.id,
                company_id=sample_company.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i + 1}",
                sequence_number=i + 1,
            )
            repository.db_session.add(message)

        await repository.db_session.commit()

        # Get latest 3 messages
        results = await repository.get_latest_by_conversation_id(
            sample_conversation.id, count=3
        )

        assert len(results) == 3
        # Should get messages 3, 4, 5 in chronological order (the method reverses them)
        assert results[0].content == "Message 3"
        assert results[1].content == "Message 4"
        assert results[2].content == "Message 5"

    async def test_get_latest_messages_no_limit(
        self, repository, sample_conversation, sample_company
    ):
        """Test getting all messages when no limit specified."""
        # Create multiple messages
        for i in range(3):
            message = MessageEntity(
                conversation_id=sample_conversation.id,
                company_id=sample_company.id,
                role="user",
                content=f"Message {i + 1}",
                sequence_number=i + 1,
            )
            repository.db_session.add(message)

        await repository.db_session.commit()

        # Get all messages (no limit)
        results = await repository.get_latest_by_conversation_id(sample_conversation.id)

        assert len(results) == 3

    async def test_message_timestamps(
        self, repository, sample_conversation, sample_company
    ):
        """Test that messages have proper timestamps."""

        message_data = MessageCreateModel(
            conversation_id=sample_conversation.id,
            company_id=sample_company.id,
            role="user",
            content="Timestamp test",
            sequence_number=1,
        )

        result = await repository.create(message_data)

        assert result.created_at is not None
        assert result.updated_at is not None
        assert result.created_at <= result.updated_at

        # Test update changes updated_at
        original_updated_at = result.updated_at
        await asyncio.sleep(0.01)  # Small delay to ensure timestamp difference
        await repository.update(
            result.id, MessageUpdateModel(content="Updated content")
        )

        updated_result = await repository.get(result.id)
        assert updated_result.updated_at >= original_updated_at

    async def test_message_with_tool_calls(
        self, repository, sample_conversation, sample_company
    ):
        """Test creating and retrieving message with tool calls."""
        # Store tool calls as raw JSON data (as they would come from the API)
        tool_calls_data = [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "get_weather", "arguments": '{"location": "NYC"}'},
            }
        ]

        message_data = MessageCreateModel(
            conversation_id=sample_conversation.id,
            company_id=sample_company.id,
            role="assistant",
            content=None,  # Assistant message with tool calls might have no content
            sequence_number=1,
            tool_calls=tool_calls_data,
        )

        result = await repository.create(message_data)

        assert result.conversation_id == sample_conversation.id
        assert result.role == "assistant"
        assert result.content is None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "call_123"
        assert result.tool_calls[0].function.name == "get_weather"

    async def test_message_with_tool_call_id(
        self, repository, sample_conversation, sample_company
    ):
        """Test creating message that responds to a tool call."""
        message_data = MessageCreateModel(
            conversation_id=sample_conversation.id,
            company_id=sample_company.id,
            role="tool",
            content="Weather is sunny, 75°F",
            sequence_number=1,
            tool_call_id="call_123",
        )

        result = await repository.create(message_data)

        assert result.conversation_id == sample_conversation.id
        assert result.role == "tool"
        assert result.content == "Weather is sunny, 75°F"
        assert result.tool_call_id == "call_123"

    async def test_message_roles_validation(
        self, repository, sample_conversation, sample_company
    ):
        """Test that different message roles can be created."""
        roles_to_test = ["user", "assistant", "system", "tool"]

        for i, role in enumerate(roles_to_test):
            message_data = MessageCreateModel(
                conversation_id=sample_conversation.id,
                company_id=sample_company.id,
                role=role,
                content=f"Message from {role}",
                sequence_number=i + 1,
            )

            result = await repository.create(message_data)

            assert result.role == role
            assert result.content == f"Message from {role}"

    async def test_bulk_create_messages(
        self, repository, sample_conversation, sample_company
    ):
        """Test bulk creating messages."""
        messages_data = [
            {
                "conversation_id": sample_conversation.id,
                "company_id": sample_company.id,
                "role": "user",
                "content": "First message",
                "sequence_number": 1,
            },
            {
                "conversation_id": sample_conversation.id,
                "company_id": sample_company.id,
                "role": "assistant",
                "content": "Second message",
                "sequence_number": 2,
            },
            {
                "conversation_id": sample_conversation.id,
                "company_id": sample_company.id,
                "role": "user",
                "content": "Third message",
                "sequence_number": 3,
            },
        ]

        # Create entities for bulk creation
        entities = [MessageEntity(**data) for data in messages_data]
        results = await repository.bulk_create(entities)

        assert len(results) == 3
        assert all(result.id is not None for result in results)

        # Verify they were created in the conversation
        conversation_messages = await repository.get_by_conversation_id(
            sample_conversation.id
        )
        assert len(conversation_messages) == 3
