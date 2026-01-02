import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from packages.questions.services.question_option_service import QuestionOptionService
from packages.questions.models.domain.question_option import (
    QuestionOptionSetCreateModel,
    QuestionOptionSetUpdateModel,
    QuestionOptionCreateModel,
)


class TestQuestionOptionService:
    """Test QuestionOptionService methods."""

    @pytest.fixture
    async def service(self, test_db: AsyncSession):
        """Create service instance."""
        return QuestionOptionService(test_db)

    async def test_create_option_set_success(self, service, sample_question):
        """Test successful creation of option set with options."""
        create_model = QuestionOptionSetCreateModel(
            options=[
                QuestionOptionCreateModel(value="Option 1"),
                QuestionOptionCreateModel(value="Option 2"),
            ],
        )

        result = await service.create_option_set(sample_question.id, create_model)

        assert result.question_id == sample_question.id
        assert len(result.options) == 2
        assert result.options[0].value == "Option 1"
        assert result.options[1].value == "Option 2"

    async def test_create_option_set_without_options(self, service, sample_question):
        """Test creating option set without options."""
        create_model = QuestionOptionSetCreateModel(options=[])
        result = await service.create_option_set(sample_question.id, create_model)

        assert result.question_id == sample_question.id
        assert len(result.options) == 0

    async def test_create_option_set_question_not_found(self, service):
        """Test creating option set for non-existent question."""
        create_model = QuestionOptionSetCreateModel(options=[])
        with pytest.raises(HTTPException) as exc_info:
            await service.create_option_set(999, create_model)

        assert exc_info.value.status_code == 404
        assert "Question not found" in str(exc_info.value.detail)

    async def test_create_option_set_already_exists(self, service, sample_question):
        """Test creating option set when one already exists."""
        # First creation
        create_model = QuestionOptionSetCreateModel(options=[])
        await service.create_option_set(sample_question.id, create_model)

        # Second creation should fail
        create_model2 = QuestionOptionSetCreateModel()

        with pytest.raises(HTTPException) as exc_info:
            await service.create_option_set(sample_question.id, create_model2)

        assert exc_info.value.status_code == 400
        assert "Option set already exists" in str(exc_info.value.detail)

    async def test_get_option_set_with_options_exists(self, service, sample_question):
        """Test getting option set with options when it exists."""
        # Create option set first
        create_model = QuestionOptionSetCreateModel(
            options=[
                QuestionOptionCreateModel(value="Option 1"),
                QuestionOptionCreateModel(value="Option 2"),
            ],
        )
        await service.create_option_set(sample_question.id, create_model)

        # Get it back
        result = await service.get_option_set_with_options(sample_question.id)

        assert result is not None
        assert result.question_id == sample_question.id
        assert len(result.options) == 2

    async def test_get_option_set_with_options_not_exists(
        self, service, sample_question
    ):
        """Test getting option set when it doesn't exist."""
        result = await service.get_option_set_with_options(sample_question.id)
        assert result is None

    async def test_update_option_set_name_only(self, service, sample_question):
        """Test updating only the option set name."""
        # Create option set first
        create_model = QuestionOptionSetCreateModel(
            options=[QuestionOptionCreateModel(value="Option 1")],
        )
        await service.create_option_set(sample_question.id, create_model)

        # Update name only
        update_model = QuestionOptionSetUpdateModel()
        result = await service.update_option_set(sample_question.id, update_model)

        assert len(result.options) == 1  # Options unchanged
        assert result.options[0].value == "Option 1"

    async def test_update_option_set_options_only(self, service, sample_question):
        """Test updating only the options."""
        # Create option set first
        create_model = QuestionOptionSetCreateModel(
            options=[QuestionOptionCreateModel(value="Old Option")],
        )
        await service.create_option_set(sample_question.id, create_model)

        # Update options only
        update_model = QuestionOptionSetUpdateModel(
            options=[
                QuestionOptionCreateModel(value="New Option 1"),
                QuestionOptionCreateModel(value="New Option 2"),
            ]
        )
        result = await service.update_option_set(sample_question.id, update_model)

        assert len(result.options) == 2
        assert result.options[0].value == "New Option 1"
        assert result.options[1].value == "New Option 2"

    async def test_update_option_set_both_name_and_options(
        self, service, sample_question
    ):
        """Test updating both name and options."""
        # Create option set first
        create_model = QuestionOptionSetCreateModel(
            options=[QuestionOptionCreateModel(value="Old Option")],
        )
        await service.create_option_set(sample_question.id, create_model)

        # Update both
        update_model = QuestionOptionSetUpdateModel(
            options=[QuestionOptionCreateModel(value="New Option")],
        )
        result = await service.update_option_set(sample_question.id, update_model)

        assert len(result.options) == 1
        assert result.options[0].value == "New Option"

    async def test_update_option_set_not_found(self, service, sample_question):
        """Test updating non-existent option set."""
        update_model = QuestionOptionSetUpdateModel()
        with pytest.raises(HTTPException) as exc_info:
            await service.update_option_set(sample_question.id, update_model)

        assert exc_info.value.status_code == 404
        assert "Option set not found" in str(exc_info.value.detail)

    async def test_delete_option_set_success(self, service, sample_question):
        """Test successful deletion of option set."""
        # Create option set first
        create_model = QuestionOptionSetCreateModel(
            options=[QuestionOptionCreateModel(value="Option 1")],
        )
        await service.create_option_set(sample_question.id, create_model)

        # Delete it
        success = await service.delete_option_set(sample_question.id)
        assert success is True

        # Verify it's gone
        result = await service.get_option_set_with_options(sample_question.id)
        assert result is None

    async def test_delete_option_set_not_found(self, service, sample_question):
        """Test deleting non-existent option set."""
        success = await service.delete_option_set(sample_question.id)
        assert success is False

    async def test_add_option_to_set_success(self, service, sample_question):
        """Test adding option to existing set."""
        # Create option set first
        create_model = QuestionOptionSetCreateModel(
            options=[QuestionOptionCreateModel(value="Option 1")],
        )
        await service.create_option_set(sample_question.id, create_model)

        # Add new option
        new_option = QuestionOptionCreateModel(value="Option 2")
        result = await service.add_option_to_set(sample_question.id, new_option)

        assert result.value == "Option 2"

        # Verify option was added
        option_set = await service.get_option_set_with_options(sample_question.id)
        assert len(option_set.options) == 2

    async def test_add_option_to_set_not_found(self, service, sample_question):
        """Test adding option to non-existent set."""
        new_option = QuestionOptionCreateModel(value="Option")

        with pytest.raises(HTTPException) as exc_info:
            await service.add_option_to_set(sample_question.id, new_option)

        assert exc_info.value.status_code == 404
        assert "Option set not found" in str(exc_info.value.detail)

    async def test_get_options_for_question_exists(self, service, sample_question):
        """Test getting options for question with option set."""
        # Create option set with options
        create_model = QuestionOptionSetCreateModel(
            options=[
                QuestionOptionCreateModel(value="Option 1"),
                QuestionOptionCreateModel(value="Option 2"),
            ],
        )
        await service.create_option_set(sample_question.id, create_model)

        # Get options
        options = await service.get_options_for_question(sample_question.id)

        assert len(options) == 2
        assert options[0].value == "Option 1"
        assert options[1].value == "Option 2"

    async def test_get_options_for_question_no_set(self, service, sample_question):
        """Test getting options for question without option set."""
        options = await service.get_options_for_question(sample_question.id)
        assert len(options) == 0

    async def test_delete_option_success(self, service, sample_question):
        """Test deleting a specific option."""
        # Create option set with options
        create_model = QuestionOptionSetCreateModel(
            options=[
                QuestionOptionCreateModel(value="Option 1"),
                QuestionOptionCreateModel(value="Option 2"),
            ],
        )
        option_set = await service.create_option_set(sample_question.id, create_model)

        # Delete first option
        option_to_delete = option_set.options[0]
        success = await service.delete_option(option_to_delete.id)
        assert success is True

        # Verify option was deleted
        remaining_options = await service.get_options_for_question(sample_question.id)
        assert len(remaining_options) == 1
        assert remaining_options[0].value == "Option 2"

    async def test_delete_option_not_found(self, service):
        """Test deleting non-existent option."""
        success = await service.delete_option(999)
        assert success is False

    async def test_service_initialization(self, test_db):
        """Test service properly initializes repositories."""
        service = QuestionOptionService(test_db)

        assert service.db_session == test_db
        assert service.option_set_repo is not None
        assert service.option_repo is not None
        assert service.question_repo is not None

    async def test_create_option_set_without_name(self, service, sample_question):
        """Test creating option set with no name (None)."""
        create_model = QuestionOptionSetCreateModel(
            options=[QuestionOptionCreateModel(value="Option 1")],
        )

        result = await service.create_option_set(sample_question.id, create_model)

        assert result.question_id == sample_question.id
        assert len(result.options) == 1
        assert result.options[0].value == "Option 1"

    async def test_update_option_set_clear_name(self, service, sample_question):
        """Test updating option set to clear the name."""
        # Create option set with name
        create_model = QuestionOptionSetCreateModel(options=[])
        await service.create_option_set(sample_question.id, create_model)

        # Update to clear name
        update_model = QuestionOptionSetUpdateModel()
        _ = await service.update_option_set(sample_question.id, update_model)

    async def test_update_option_set_empty_options_list(self, service, sample_question):
        """Test updating option set with empty options list."""
        # Create option set with options
        create_model = QuestionOptionSetCreateModel(
            options=[QuestionOptionCreateModel(value="Option 1")],
        )
        await service.create_option_set(sample_question.id, create_model)

        # Update with empty options list
        update_model = QuestionOptionSetUpdateModel(options=[])
        result = await service.update_option_set(sample_question.id, update_model)

        assert len(result.options) == 0
