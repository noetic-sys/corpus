import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from packages.agents.repositories.conversation_repository import ConversationRepository
from packages.agents.models.database.conversation import ConversationEntity
from packages.agents.models.domain.conversation import (
    ConversationCreateModel,
    ConversationUpdateModel,
)
from packages.ai_model.models.database.ai_model import AIModelEntity


class TestConversationRepository:
    """Test ConversationRepository methods."""

    @pytest.fixture
    async def repository(self, test_db: AsyncSession):
        """Create repository instance."""
        return ConversationRepository(test_db)

    async def test_create_conversation_success(
        self, repository, sample_ai_model, sample_company
    ):
        """Test successful conversation creation."""
        conversation_data = ConversationCreateModel(
            title="New Conversation",
            company_id=sample_company.id,
            ai_model_id=sample_ai_model.id,
            extra_data={"key": "value"},
        )

        result = await repository.create(conversation_data)

        assert result.title == "New Conversation"
        assert result.ai_model_id == sample_ai_model.id
        assert result.extra_data == {"key": "value"}
        assert result.is_active is True
        assert result.id is not None

    async def test_get_conversation_exists(self, repository, sample_conversation):
        """Test getting existing conversation."""
        result = await repository.get(sample_conversation.id)

        assert result is not None
        assert result.id == sample_conversation.id
        assert result.title == sample_conversation.title
        assert result.ai_model_id == sample_conversation.ai_model_id

    async def test_get_conversation_not_exists(self, repository):
        """Test getting non-existent conversation."""
        result = await repository.get(999)
        assert result is None

    async def test_update_conversation_success(self, repository, sample_conversation):
        """Test successful conversation update."""
        update_data = ConversationUpdateModel(
            title="Updated Conversation",
            extra_data={"updated": True},
        )

        result = await repository.update(sample_conversation.id, update_data)

        assert result is not None
        assert result.title == "Updated Conversation"
        assert result.extra_data == {"updated": True}
        assert result.ai_model_id == sample_conversation.ai_model_id  # Unchanged

    async def test_update_conversation_partial(self, repository, sample_conversation):
        """Test partial conversation update."""
        update_data = ConversationUpdateModel(title="Only Title Updated")

        result = await repository.update(sample_conversation.id, update_data)

        assert result is not None
        assert result.title == "Only Title Updated"
        assert result.ai_model_id == sample_conversation.ai_model_id  # Unchanged

    async def test_update_conversation_not_found(self, repository):
        """Test updating non-existent conversation."""
        update_data = ConversationUpdateModel(title="Updated")

        result = await repository.update(999, update_data)
        assert result is None

    async def test_delete_conversation_success(self, repository, sample_conversation):
        """Test successful conversation deletion (soft delete)."""
        success = await repository.soft_delete(sample_conversation.id)
        assert success is True

        # Verify conversation is soft deleted
        result = await repository.get(sample_conversation.id)
        assert result is None

    async def test_delete_conversation_not_found(self, repository):
        """Test deleting non-existent conversation."""
        success = await repository.soft_delete(999)
        assert success is False

    async def test_list_conversations_active_only(
        self, repository, sample_ai_model, sample_company
    ):
        """Test listing only active conversations."""
        # Create active and inactive conversations
        active_conv = ConversationEntity(
            title="Active Conversation",
            ai_model_id=sample_ai_model.id,
            is_active=True,
            company_id=sample_company.id,
        )
        inactive_conv = ConversationEntity(
            title="Inactive Conversation",
            ai_model_id=sample_ai_model.id,
            is_active=False,
            company_id=sample_company.id,
        )

        repository.db_session.add_all([active_conv, inactive_conv])
        await repository.db_session.commit()

        # Get all active conversations
        results = await repository.get_all()

        # Should only return active conversations
        active_titles = [conv.title for conv in results]
        assert "Active Conversation" in active_titles
        assert "Inactive Conversation" not in active_titles

    async def test_list_conversations_pagination(
        self, repository, sample_ai_model, sample_company
    ):
        """Test listing conversations with pagination."""
        # Create multiple conversations
        conversations = []
        for i in range(5):
            conv = ConversationEntity(
                title=f"Conversation {i}",
                ai_model_id=sample_ai_model.id,
                is_active=True,
                company_id=sample_company.id,
            )
            conversations.append(conv)

        repository.db_session.add_all(conversations)
        await repository.db_session.commit()

        # Test pagination
        page_1 = await repository.get_all(skip=0, limit=2)
        page_2 = await repository.get_all(skip=2, limit=2)

        assert len(page_1) == 2
        assert len(page_2) == 2

        # Ensure no overlap
        page_1_ids = {conv.id for conv in page_1}
        page_2_ids = {conv.id for conv in page_2}
        assert page_1_ids.isdisjoint(page_2_ids)

    async def test_get_by_ai_model_id(
        self, repository, sample_ai_model, sample_ai_provider, sample_company
    ):
        """Test getting conversations by AI model ID."""
        # Create another AI model
        other_model = AIModelEntity(
            provider_id=sample_ai_provider.id,
            model_name="gpt-3.5-turbo",
            display_name="GPT-3.5 Turbo",
            default_temperature=0.7,
            enabled=True,
        )
        repository.db_session.add(other_model)
        await repository.db_session.commit()
        await repository.db_session.refresh(other_model)

        # Create conversations with different models
        conv1 = ConversationEntity(
            title="Conversation with Model 1",
            ai_model_id=sample_ai_model.id,
            is_active=True,
            company_id=sample_company.id,
        )
        conv2 = ConversationEntity(
            title="Conversation with Model 2",
            ai_model_id=other_model.id,
            is_active=True,
            company_id=sample_company.id,
        )
        conv3 = ConversationEntity(
            title="Another Conversation with Model 1",
            ai_model_id=sample_ai_model.id,
            is_active=True,
            company_id=sample_company.id,
        )

        repository.db_session.add_all([conv1, conv2, conv3])
        await repository.db_session.commit()

        # Get conversations for first model
        results = await repository.get_by_ai_model_id(sample_ai_model.id)

        assert len(results) == 2
        titles = [conv.title for conv in results]
        assert "Conversation with Model 1" in titles
        assert "Another Conversation with Model 1" in titles
        assert "Conversation with Model 2" not in titles

    async def test_get_by_ai_model_id_no_results(self, repository):
        """Test getting conversations for AI model with no conversations."""
        results = await repository.get_by_ai_model_id(999)
        assert len(results) == 0

    async def test_deactivate_conversation(self, repository, sample_conversation):
        """Test deactivating a conversation."""
        # Ensure conversation is initially active
        assert sample_conversation.is_active is True

        # Deactivate
        result = await repository.update(
            sample_conversation.id, ConversationUpdateModel(is_active=False)
        )

        assert result is not None
        assert result.is_active is False

        # Verify it doesn't appear in active list
        active_conversations = await repository.get_all()
        active_ids = [conv.id for conv in active_conversations]
        assert sample_conversation.id not in active_ids

    async def test_conversation_timestamps(self, repository, sample_company):
        """Test that conversations have proper timestamps."""

        conversation_data = ConversationCreateModel(
            title="Timestamp Test", company_id=sample_company.id
        )

        result = await repository.create(conversation_data)

        assert result.created_at is not None
        assert result.updated_at is not None
        assert result.created_at <= result.updated_at

        # Test update changes updated_at - add small delay to ensure timestamp difference
        original_updated_at = result.updated_at
        await asyncio.sleep(0.01)  # Small delay to ensure timestamp difference
        await repository.update(
            result.id, ConversationUpdateModel(title="Updated Title")
        )

        updated_result = await repository.get(result.id)
        assert updated_result.updated_at >= original_updated_at

    async def test_conversation_with_null_fields(self, repository, sample_company):
        """Test creating and updating conversation with null fields."""
        # Create with nulls
        conversation_data = ConversationCreateModel(
            title="Null Fields Test",
            company_id=sample_company.id,
            ai_model_id=None,
            extra_data=None,
        )

        result = await repository.create(conversation_data)

        assert result.title == "Null Fields Test"
        assert result.ai_model_id is None
        assert result.extra_data is None

        # Update to set values
        update_data = ConversationUpdateModel(
            extra_data={"now": "has_data"},
        )

        updated_result = await repository.update(result.id, update_data)

        assert updated_result.extra_data == {"now": "has_data"}

        # Update to clear values
        clear_data = ConversationUpdateModel(extra_data=None)

        cleared_result = await repository.update(result.id, clear_data)

        assert cleared_result.extra_data is None
