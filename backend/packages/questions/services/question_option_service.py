from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from packages.questions.repositories.question_option_repository import (
    QuestionOptionSetRepository,
    QuestionOptionRepository,
)
from packages.questions.repositories.question_repository import QuestionRepository
from packages.questions.models.domain.question_option import (
    QuestionOptionSetCreateModel,
    QuestionOptionSetUpdateModel,
    QuestionOptionSetWithOptionsModel,
    QuestionOptionModel,
    QuestionOptionCreateModel,
)
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class QuestionOptionService:
    """Service for handling question option set operations."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.option_set_repo = QuestionOptionSetRepository(db_session)
        self.option_repo = QuestionOptionRepository(db_session)
        self.question_repo = QuestionRepository(db_session)

    @trace_span
    async def create_option_set(
        self, question_id: int, create_model: QuestionOptionSetCreateModel
    ) -> QuestionOptionSetWithOptionsModel:
        """Create a new option set with options for a question."""
        logger.info(f"Creating option set for question {question_id}")

        # Verify question exists
        question = await self.question_repo.get(question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Check if option set already exists for this question
        existing_set = await self.option_set_repo.get_by_question_id(question_id)
        if existing_set:
            raise HTTPException(
                status_code=400, detail="Option set already exists for this question"
            )

        # Create the option set
        option_set = await self.option_set_repo.create_for_question(question_id)

        # Create the options if provided
        if create_model.options:
            await self.option_repo.bulk_create_for_set(
                option_set.id, create_model.options
            )

        logger.info(f"Created option set with ID: {option_set.id}")
        return await self.get_option_set_with_options(question_id)

    @trace_span
    async def get_option_set_with_options(
        self, question_id: int
    ) -> Optional[QuestionOptionSetWithOptionsModel]:
        """Get option set and all its options for a question."""
        option_set = await self.option_set_repo.get_by_question_id(question_id)
        if not option_set:
            return None

        # Get the options separately as required (no selectinload)
        options = await self.option_repo.get_by_option_set_id(option_set.id)

        # Create composite model at service level
        return QuestionOptionSetWithOptionsModel(
            id=option_set.id,
            question_id=option_set.question_id,
            created_at=option_set.created_at,
            updated_at=option_set.updated_at,
            options=options,
        )

    @trace_span
    async def update_option_set(
        self, question_id: int, update_model: QuestionOptionSetUpdateModel
    ) -> Optional[QuestionOptionSetWithOptionsModel]:
        """Update an existing option set."""
        logger.info(f"Updating option set for question {question_id}")

        option_set = await self.option_set_repo.get_by_question_id(question_id)
        if not option_set:
            raise HTTPException(status_code=404, detail="Option set not found")

        # Update the option set if needed
        _ = update_model.model_dump(exclude_unset=True)

        # Replace options if provided
        if update_model.options is not None:
            await self.option_repo.replace_all_for_set(
                option_set.id, update_model.options
            )

        logger.info(f"Updated option set for question {question_id}")
        return await self.get_option_set_with_options(question_id)

    @trace_span
    async def delete_option_set(self, question_id: int) -> bool:
        """Delete option set and all its options for a question."""
        logger.info(f"Deleting option set for question {question_id}")

        success = await self.option_set_repo.delete_by_question_id(question_id)
        if success:
            logger.info(f"Deleted option set for question {question_id}")
        return success

    @trace_span
    async def add_option_to_set(
        self, question_id: int, option_create: QuestionOptionCreateModel
    ) -> QuestionOptionModel:
        """Add a single option to an existing option set."""
        option_set = await self.option_set_repo.get_by_question_id(question_id)
        if not option_set:
            raise HTTPException(status_code=404, detail="Option set not found")

        option = await self.option_repo.create_for_set(option_set.id, option_create)
        logger.info(f"Added option to set {option_set.id}")
        return option

    @trace_span
    async def get_options_for_question(
        self, question_id: int
    ) -> List[QuestionOptionModel]:
        """Get all options for a question."""
        option_set = await self.option_set_repo.get_by_question_id(question_id)
        if not option_set:
            return []

        return await self.option_repo.get_by_option_set_id(option_set.id)

    @trace_span
    async def delete_option(self, option_id: int) -> bool:
        """Delete a specific option."""
        success = await self.option_repo.delete(option_id)
        if success:
            logger.info(f"Deleted option {option_id}")
        return success


def get_question_option_service(db_session: AsyncSession) -> QuestionOptionService:
    """Get question option service instance."""
    return QuestionOptionService(db_session)
