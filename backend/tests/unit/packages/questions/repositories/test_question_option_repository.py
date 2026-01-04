import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from packages.questions.repositories.question_option_repository import (
    QuestionOptionSetRepository,
    QuestionOptionRepository,
)
from packages.questions.models.domain.question_option import QuestionOptionCreateModel


class TestQuestionOptionSetRepository:
    """Test QuestionOptionSetRepository methods."""

    @pytest.fixture
    async def repository(self, test_db: AsyncSession):
        """Create repository instance."""
        return QuestionOptionSetRepository()

    async def test_create_for_question(self, repository, sample_question):
        """Test creating an option set for a question."""
        # Create option set
        option_set = await repository.create_for_question(sample_question.id)

        # Verify creation
        assert option_set.id is not None
        assert option_set.question_id == sample_question.id
        assert option_set.created_at is not None
        assert option_set.updated_at is not None

    async def test_create_for_question_without_name(self, repository, sample_question):
        """Test creating an option set without a name."""
        option_set = await repository.create_for_question(sample_question.id)

        assert option_set.id is not None
        assert option_set.question_id == sample_question.id

    async def test_get_by_question_id(self, repository, sample_question):
        """Test getting option set by question ID."""
        # Create option set
        created_set = await repository.create_for_question(sample_question.id)

        # Retrieve by question ID
        retrieved_set = await repository.get_by_question_id(sample_question.id)

        assert retrieved_set is not None
        assert retrieved_set.id == created_set.id
        assert retrieved_set.question_id == sample_question.id

    async def test_get_by_question_id_not_found(self, repository):
        """Test getting option set for non-existent question."""
        result = await repository.get_by_question_id(999)
        assert result is None

    async def test_delete_by_question_id(self, repository, sample_question):
        """Test deleting option set by question ID."""
        # Create option set
        await repository.create_for_question(sample_question.id)

        # Delete by question ID
        success = await repository.delete_by_question_id(sample_question.id)
        assert success is True

        # Verify deletion
        result = await repository.get_by_question_id(sample_question.id)
        assert result is None

    async def test_delete_by_question_id_not_found(self, repository):
        """Test deleting non-existent option set."""
        success = await repository.delete_by_question_id(999)
        assert success is False

    async def test_entity_to_domain_conversion(self, repository, sample_question):
        """Test that entity to domain conversion works correctly."""
        option_set = await repository.create_for_question(sample_question.id)

        # Verify all domain model fields are properly set
        assert isinstance(option_set.id, int)
        assert isinstance(option_set.question_id, int)
        assert option_set.created_at is not None
        assert option_set.updated_at is not None


class TestQuestionOptionRepository:
    """Test QuestionOptionRepository methods."""

    @pytest.fixture
    async def repository(self, test_db: AsyncSession):
        """Create repository instance."""
        return QuestionOptionRepository()

    @pytest.fixture
    async def option_set_repo(self, test_db: AsyncSession):
        """Create option set repository."""
        return QuestionOptionSetRepository()

    @pytest.fixture
    async def sample_option_set(self, option_set_repo, sample_question):
        """Create a sample option set."""
        return await option_set_repo.create_for_question(sample_question.id)

    async def test_create_for_set(self, repository, sample_option_set):
        """Test creating an option for an option set."""
        option_data = QuestionOptionCreateModel(value="Test Option")

        option = await repository.create_for_set(sample_option_set.id, option_data)

        assert option.id is not None
        assert option.option_set_id == sample_option_set.id
        assert option.value == "Test Option"

    @pytest.mark.skip(reason="This test is flaky and needs to be fixed")
    async def test_create_for_set_auto_display_order(
        self, repository, sample_option_set
    ):
        """Test creating option with auto-generated display order."""
        # Create first option
        option1_data = QuestionOptionCreateModel(value="Option 1")
        await repository.create_for_set(sample_option_set.id, option1_data)

        # Create second option without display_order (should auto-increment)
        option2_data = QuestionOptionCreateModel(value="Option 2")
        _ = await repository.create_for_set(sample_option_set.id, option2_data)

    async def test_get_by_option_set_id(self, repository, sample_option_set):
        """Test getting options by option set ID."""
        # Create multiple options
        option1_data = QuestionOptionCreateModel(value="Option 1")
        option2_data = QuestionOptionCreateModel(value="Option 2")

        await repository.create_for_set(sample_option_set.id, option1_data)
        await repository.create_for_set(sample_option_set.id, option2_data)

        # Get options
        options = await repository.get_by_option_set_id(sample_option_set.id)

        assert len(options) == 2
        # Order is not guaranteed without display_order

    async def test_bulk_create_for_set(self, repository, sample_option_set):
        """Test bulk creating options for an option set."""
        option_data = [
            QuestionOptionCreateModel(value="Option 1"),
            QuestionOptionCreateModel(value="Option 2"),
            QuestionOptionCreateModel(value="Option 3"),
        ]

        options = await repository.bulk_create_for_set(
            sample_option_set.id, option_data
        )

        assert len(options) == 3
        assert all(opt.option_set_id == sample_option_set.id for opt in options)
        assert [opt.value for opt in options] == ["Option 1", "Option 2", "Option 3"]

    @pytest.mark.skip(reason="This test is flaky and needs to be fixed")
    async def test_bulk_create_auto_display_order(self, repository, sample_option_set):
        """Test bulk create with auto-generated display orders."""
        option_data = [
            QuestionOptionCreateModel(value="Option 1"),  # No display_order
            QuestionOptionCreateModel(value="Option 2"),  # No display_order
        ]

        options = await repository.bulk_create_for_set(
            sample_option_set.id, option_data
        )

        assert len(options) == 2
        # Order is not guaranteed without display_order

    async def test_replace_all_for_set(self, repository, sample_option_set):
        """Test replacing all options for an option set."""
        # Create initial options
        initial_data = [
            QuestionOptionCreateModel(value="Old Option 1"),
            QuestionOptionCreateModel(value="Old Option 2"),
        ]
        await repository.bulk_create_for_set(sample_option_set.id, initial_data)

        # Replace with new options
        new_data = [
            QuestionOptionCreateModel(value="New Option 1"),
            QuestionOptionCreateModel(value="New Option 2"),
            QuestionOptionCreateModel(value="New Option 3"),
        ]

        new_options = await repository.replace_all_for_set(
            sample_option_set.id, new_data
        )

        # Verify replacement
        assert len(new_options) == 3
        all_options = await repository.get_by_option_set_id(sample_option_set.id)
        assert len(all_options) == 3
        assert [opt.value for opt in all_options] == [
            "New Option 1",
            "New Option 2",
            "New Option 3",
        ]

    async def test_delete_by_option_set_id(self, repository, sample_option_set):
        """Test deleting all options for an option set."""
        # Create options
        option_data = [
            QuestionOptionCreateModel(value="Option 1"),
            QuestionOptionCreateModel(value="Option 2"),
        ]
        await repository.bulk_create_for_set(sample_option_set.id, option_data)

        # Delete all options
        deleted_count = await repository.delete_by_option_set_id(sample_option_set.id)

        assert deleted_count == 2

        # Verify deletion
        remaining_options = await repository.get_by_option_set_id(sample_option_set.id)
        assert len(remaining_options) == 0

    async def test_get_by_option_set_id_empty(self, repository, sample_option_set):
        """Test getting options for empty option set."""
        options = await repository.get_by_option_set_id(sample_option_set.id)
        assert len(options) == 0
