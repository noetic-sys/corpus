from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from common.core.otel_axiom_exporter import trace_span, get_logger
from common.providers.caching import get_cache_provider
from packages.qa.repositories.answer_repository import AnswerRepository
from packages.qa.models.domain.answer import (
    AnswerModel,
    AnswerCreateModel,
    AnswerUpdateModel,
)
from packages.qa.cache_keys import answers_by_answer_set_key

logger = get_logger(__name__)


class AnswerService:
    """Service for handling individual answer operations."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.answer_repo = AnswerRepository(db_session)

    @trace_span
    async def create_answer(
        self, answer_data: AnswerCreateModel, company_id: int
    ) -> AnswerModel:
        """Create a new answer."""
        logger.info(f"Creating answer for answer set {answer_data.answer_set_id}")

        # Ensure company_id matches
        if answer_data.company_id != company_id:
            raise ValueError("Answer company_id must match the provided company_id")

        answer = await self.answer_repo.create(answer_data)
        logger.info(f"Created answer with ID: {answer.id}")
        return answer

    @trace_span
    async def get_answer(
        self, answer_id: int, company_id: Optional[int] = None
    ) -> Optional[AnswerModel]:
        """Get an answer by ID."""
        answer = await self.answer_repo.get(answer_id)
        if answer and company_id is not None and answer.company_id != company_id:
            return None
        return answer

    @trace_span
    async def get_answers_for_answer_set(
        self, answer_set_id: int, company_id: Optional[int] = None
    ) -> List[AnswerModel]:
        """Get all answers for an answer set."""
        return await self.answer_repo.get_by_answer_set_id(answer_set_id, company_id)

    @trace_span
    async def get_by_answer_set_ids(
        self, answer_set_ids: List[int], company_id: Optional[int] = None
    ) -> List[AnswerModel]:
        """Batch fetch all answers for multiple answer sets."""
        return await self.answer_repo.get_by_answer_set_ids(answer_set_ids, company_id)

    @trace_span
    async def bulk_create_answers(
        self, answer_data_list: List[AnswerCreateModel], company_id: int
    ) -> List[AnswerModel]:
        """Bulk create multiple answers for an answer set."""
        if not answer_data_list:
            return []

        logger.info(f"Bulk creating {len(answer_data_list)} answers")

        # Validate all company_ids match
        for answer_data in answer_data_list:
            if answer_data.company_id != company_id:
                raise ValueError(
                    "All answer company_ids must match the provided company_id"
                )
        # Use repository bulk create method
        answers = []
        for answer_data in answer_data_list:
            answer = await self.answer_repo.create(answer_data)
            answers.append(answer)

        logger.info(f"Created {len(answers)} answers")
        return answers

    @trace_span
    async def update_answer(
        self,
        answer_id: int,
        update_data: AnswerUpdateModel,
        company_id: Optional[int] = None,
    ) -> Optional[AnswerModel]:
        """Update an answer with the provided data."""
        logger.info(f"Updating answer {answer_id} with data: {update_data}")

        # Get existing answer to know answer_set_id for cache invalidation
        existing_answer = await self.answer_repo.get(answer_id)
        if not existing_answer:
            logger.warning(f"Answer {answer_id} not found for update")
            return None

        # Check company access if company_id provided
        if company_id is not None and existing_answer.company_id != company_id:
            logger.warning(f"Answer {answer_id} access denied for company {company_id}")
            return None

        answer = await self.answer_repo.update(answer_id, update_data)
        if answer:
            logger.info(f"Successfully updated answer {answer_id}")

            # Invalidate cache for get_by_answer_set_id
            try:
                cache_provider = get_cache_provider()

                # Generate specific cache keys for this answer_set_id
                cache_key_no_company = answers_by_answer_set_key(
                    existing_answer.answer_set_id, None
                )
                cache_key_with_company = answers_by_answer_set_key(
                    existing_answer.answer_set_id, existing_answer.company_id
                )

                # Invalidate both variations
                await cache_provider.delete_pattern(cache_key_no_company)
                await cache_provider.delete_pattern(cache_key_with_company)

                logger.info(
                    f"Invalidated answer cache for answer_set_id {existing_answer.answer_set_id}"
                )

            except Exception as e:
                logger.warning(f"Cache invalidation failed for answer {answer_id}: {e}")

        return answer
